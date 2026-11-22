import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jose import jwt
from jose.utils import base64url_encode
from pydantic import ValidationError
from uuid import uuid4

from app.core.config import settings
from app.core.deps import verify_supabase_jwt
from app.main import app, ai_chat, parse_course_id
from app.api.auth import forgot_password, login, signup
from app.models.models import User
from app.schemas.api import (
    AIChatRequest,
    AssignmentSubmission,
    ForgotPasswordRequest,
    LoginRequest,
    QuizQuestionCreate,
    SignupRequest,
)
from app.services.rag import chunk_transcript
from app.services.transcript import extract_video_url, extract_youtube_id, get_video_transcript


class APIAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/api/v1/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "healthy"})

    def test_malformed_token_is_rejected(self):
        response = self.client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        self.assertEqual(response.status_code, 401)

    def test_token_with_invalid_signature_is_rejected(self):
        token = jwt.encode(
            {"sub": "00000000-0000-0000-0000-000000000001", "email": "student@example.com"},
            "not-the-project-secret",
            algorithm="HS256",
        )
        response = self.client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        expected_status = 503 if settings.SUPABASE_JWT_SECRET == "placeholder-jwt-secret" else 401
        self.assertEqual(response.status_code, expected_status)

    def test_hs256_token_is_verified_when_secret_is_configured(self):
        if settings.SUPABASE_JWT_SECRET == "placeholder-jwt-secret":
            self.skipTest("No Supabase HS256 secret is configured")

        token = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000001",
                "email": "student@example.com",
                "exp": int(time.time()) + 60,
            },
            settings.SUPABASE_JWT_SECRET,
            algorithm="HS256",
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        payload = asyncio.run(verify_supabase_jwt(credentials))
        self.assertEqual(payload["email"], "student@example.com")

    def test_es256_supabase_token_is_verified_with_jwks(self):
        private_key = ec.generate_private_key(ec.SECP256R1())
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_numbers = private_key.public_key().public_numbers()

        def encode_coordinate(value):
            return base64url_encode(value.to_bytes(32, "big")).decode("ascii")

        jwk = {
            "kty": "EC",
            "crv": "P-256",
            "x": encode_coordinate(public_numbers.x),
            "y": encode_coordinate(public_numbers.y),
            "kid": "test-key",
            "alg": "ES256",
            "use": "sig",
        }
        token = jwt.encode(
            {
                "sub": "00000000-0000-0000-0000-000000000001",
                "email": "student@example.com",
                "exp": int(time.time()) + 60,
            },
            private_key_pem,
            algorithm="ES256",
            headers={"kid": "test-key"},
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("app.core.deps.get_supabase_jwks", new=AsyncMock(return_value=[jwk])):
            payload = asyncio.run(verify_supabase_jwt(credentials))

        self.assertEqual(payload["email"], "student@example.com")

    def test_api_exposes_required_mvp_routes(self):
        response = self.client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/v1/courses/{course_id}/enroll", paths)
        self.assertIn("/api/v1/quizzes/{quiz_id}/attempt", paths)
        self.assertIn("/api/v1/submissions/{submission_id}/grade", paths)
        self.assertIn("/api/v1/admin/users/{user_id}", paths)

    def test_preflight_allows_loopback_frontend_origin(self):
        response = self.client.options(
            "/api/v1/courses",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:3000",
        )


class VideoTranscriptTests(unittest.TestCase):
    def test_invalid_page_context_course_id_does_not_block_chat(self):
        self.assertIsNone(parse_course_id("1"))

    def test_chat_answers_and_summarizes_direct_page_context_without_valid_course_id(self):
        response = SimpleNamespace(
            message=SimpleNamespace(content=[SimpleNamespace(text="Here is the summary.")])
        )
        cohere_client = SimpleNamespace(chat=Mock(return_value=response))
        request = AIChatRequest(
            prompt="could you summary this page",
            page_context={
                "courseId": "1",
                "lessonTitle": "Variables and Data Types",
                "contentBody": "Variables store values. Python has numeric and string data types.",
            },
        )

        with patch("app.main.co", cohere_client):
            result = asyncio.run(ai_chat(request, AsyncMock(), object()))

        self.assertEqual(result["response"], "Here is the summary.")
        chat_args = cohere_client.chat.call_args.kwargs
        self.assertEqual(chat_args["model"], "command-a-03-2025")
        self.assertIn("Variables store values", chat_args["messages"][0]["content"])
        self.assertIn("summarize the Direct Lesson Content", chat_args["messages"][0]["content"])

    def test_extract_youtube_id_supports_watch_and_embed_urls(self):
        self.assertEqual(
            extract_youtube_id("https://www.youtube.com/watch?v=abcdefghijk"),
            "abcdefghijk",
        )
        self.assertEqual(
            extract_youtube_id("https://youtube-nocookie.com/embed/abcdefghijk"),
            "abcdefghijk",
        )

    def test_prompt_video_url_extraction_preserves_non_youtube_links_for_diagnosis(self):
        url = extract_video_url("Can you explain https://example.com/lecture.mp4?")
        self.assertEqual(url, "https://example.com/lecture.mp4")
        self.assertIsNone(extract_youtube_id(url))

    def test_video_transcript_reports_not_youtube_without_network_access(self):
        result = asyncio.run(get_video_transcript("https://example.com/lecture.mp4"))
        self.assertEqual(result.reason, "not_youtube")

    def test_caption_fetch_preserves_exception_type_for_diagnostics(self):
        with patch(
            "app.services.transcript._fetch_youtube_transcript",
            side_effect=RuntimeError("request failed"),
        ):
            result = asyncio.run(
                get_video_transcript("https://www.youtube.com/watch?v=abcdefghijk")
            )
        self.assertEqual(result.reason, "youtube_error")
        self.assertEqual(result.exception_type, "RuntimeError")

    def test_transcript_chunks_stay_under_one_thousand_characters(self):
        chunks = chunk_transcript(("Arabic and English learning text. " * 100))
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(0 < len(chunk) <= 1000 for chunk in chunks))


class AdminLoginTests(unittest.TestCase):
    def test_admin_can_login_after_bootstrap_without_bootstrap_password_env(self):
        user_id = uuid4()
        profile = User(
            id=user_id,
            email=settings.ADMIN_EMAIL,
            full_name="Platform Admin",
            role="admin",
            is_active=True,
        )
        db_result = Mock()
        db_result.scalar_one_or_none.return_value = profile
        db = AsyncMock()
        db.execute.return_value = db_result

        class FakeResponse:
            is_error = False

            @staticmethod
            def json():
                return {
                    "user": {
                        "id": str(user_id),
                        "email": settings.ADMIN_EMAIL,
                        "user_metadata": {"full_name": "Platform Admin", "role": "student"},
                    },
                    "access_token": "supabase-access-token",
                    "refresh_token": "supabase-refresh-token",
                }

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with (
            patch("app.api.auth.settings.SUPABASE_ANON_KEY", "test-anon-key"),
            patch("app.api.auth.settings.SUPABASE_SERVICE_ROLE_KEY", ""),
            patch("app.api.auth.settings.BOOTSTRAP_ADMIN_EMAIL", ""),
            patch("app.api.auth.settings.BOOTSTRAP_ADMIN_PASSWORD", ""),
            patch("app.api.auth.httpx.AsyncClient", return_value=FakeAsyncClient()),
        ):
            result = asyncio.run(
                login(
                    LoginRequest(email=settings.ADMIN_EMAIL, password="supabase-password"),
                    db,
                )
            )

        self.assertEqual(result["role"], "admin")
        self.assertEqual(result["dashboard"], "/admin/dashboard")

    def test_password_recovery_uses_reset_page_redirect_and_generic_response(self):
        class FakeResponse:
            is_error = False

        class FakeAsyncClient:
            request_args = None

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def post(self, *args, **kwargs):
                self.request_args = (args, kwargs)
                return FakeResponse()

        client = FakeAsyncClient()
        with (
            patch("app.api.auth.settings.SUPABASE_ANON_KEY", "test-anon-key"),
            patch("app.api.auth.settings.FRONTEND_ORIGINS", ["http://localhost:3000"]),
            patch("app.api.auth.httpx.AsyncClient", return_value=client),
        ):
            result = asyncio.run(
                forgot_password(ForgotPasswordRequest(email="student@example.com"))
            )

        self.assertIn("If an account exists", result["message"])
        self.assertEqual(
            client.request_args[1]["params"]["redirect_to"],
            "http://localhost:3000/reset-password",
        )

    def test_password_recovery_reports_transport_error_type(self):
        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def post(self, *args, **kwargs):
                raise httpx.ConnectTimeout("connection timed out")

        with (
            patch("app.api.auth.settings.SUPABASE_ANON_KEY", "test-anon-key"),
            patch("app.api.auth.httpx.AsyncClient", return_value=FakeAsyncClient()),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    forgot_password(
                        ForgotPasswordRequest(email="student@example.com")
                    )
                )

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("ConnectTimeout", context.exception.detail)

    def test_password_recovery_exposes_safe_supabase_error_code(self):
        class FakeResponse:
            is_error = True
            status_code = 429

            @staticmethod
            def json():
                return {"error_code": "over_email_send_rate_limit"}

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with (
            patch("app.api.auth.settings.SUPABASE_ANON_KEY", "test-anon-key"),
            patch("app.api.auth.httpx.AsyncClient", return_value=FakeAsyncClient()),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    forgot_password(
                        ForgotPasswordRequest(email="student@example.com")
                    )
                )

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("over_email_send_rate_limit", context.exception.detail)

    def test_password_recovery_explains_supabase_email_gateway_timeout(self):
        class FakeResponse:
            is_error = True
            status_code = 504

            @staticmethod
            def json():
                return {}

        class FakeAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with (
            patch("app.api.auth.settings.SUPABASE_ANON_KEY", "test-anon-key"),
            patch("app.api.auth.httpx.AsyncClient", return_value=FakeAsyncClient()),
        ):
            with self.assertRaises(HTTPException) as context:
                asyncio.run(
                    forgot_password(
                        ForgotPasswordRequest(email="student@example.com")
                    )
                )

        self.assertIn("timed out while sending the recovery email", context.exception.detail)
        self.assertIn("SMTP", context.exception.detail)

    def test_signup_redirects_confirmation_email_to_frontend_callback(self):
        user_id = uuid4()
        empty_result = Mock()
        empty_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.add = Mock()
        db.execute.side_effect = [empty_result, empty_result]

        class FakeResponse:
            is_error = False

            @staticmethod
            def json():
                return {
                    "user": {
                        "id": str(user_id),
                        "email": "new-student@example.com",
                    },
                    "session": {
                        "access_token": "access",
                        "refresh_token": "refresh",
                    },
                }

        class FakeAsyncClient:
            request_args = None

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def post(self, *args, **kwargs):
                self.request_args = (args, kwargs)
                return FakeResponse()

        client = FakeAsyncClient()
        with (
            patch("app.api.auth.settings.SUPABASE_ANON_KEY", "test-anon-key"),
            patch("app.api.auth.settings.FRONTEND_ORIGINS", ["http://localhost:3000"]),
            patch("app.api.auth.httpx.AsyncClient", return_value=client),
        ):
            result = asyncio.run(
                signup(
                    SignupRequest(
                        email="new-student@example.com",
                        password="valid-password",
                        full_name="New Student",
                        role="student",
                    ),
                    db,
                )
            )

        self.assertEqual(result["dashboard"], "/student/dashboard")
        self.assertEqual(
            client.request_args[1]["params"]["redirect_to"],
            "http://localhost:3000/auth/confirm",
        )

    def test_reserved_admin_email_cannot_use_public_signup(self):
        with self.assertRaises(HTTPException) as context:
            asyncio.run(
                signup(
                    SignupRequest(
                        email=settings.ADMIN_EMAIL,
                        password="valid-password",
                        full_name="Platform Admin",
                        role="student",
                    ),
                    AsyncMock(),
                )
            )
        self.assertEqual(context.exception.status_code, 403)

    def test_assignment_requires_a_real_link_or_text_response(self):
        with self.assertRaises(ValidationError):
            AssignmentSubmission()
        with self.assertRaises(ValidationError):
            AssignmentSubmission(file_url="javascript:alert(1)")

    def test_quiz_correct_answer_must_be_one_of_the_options(self):
        with self.assertRaises(ValidationError):
            QuizQuestionCreate(
                question_text="Which answer is correct?",
                options=["A", "B"],
                correct_answer="C",
            )


if __name__ == "__main__":
    unittest.main()
