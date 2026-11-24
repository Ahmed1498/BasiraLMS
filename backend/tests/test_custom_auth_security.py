import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException, Request, Response
from unittest.mock import AsyncMock, Mock, patch

from app.api import auth
from app.core.config import settings
from app.models.models import AuthToken, User


def make_request(host: str, cookie: str | None = None) -> Request:
    headers = [] if cookie is None else [(b"cookie", cookie.encode("latin-1"))]
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": headers,
            "client": (host, 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def result_with_scalar(value):
    result = Mock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.all.return_value = []
    return result


def make_user(email: str = "student@example.com", role: str = "student") -> User:
    return User(
        id=uuid4(),
        email=email,
        full_name="Test User",
        role=role,
        is_active=True,
        password_hash="test-hash",
        email_verified=True,
        failed_login_attempts=0,
        locked_until=None,
    )


def make_token(raw_token: str, user_id, purpose: str, expires_at) -> AuthToken:
    return AuthToken(
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        user_id=user_id,
        purpose=purpose,
        expires_at=expires_at,
        used_at=None,
    )


def test_refresh_token_rotation_rejects_reuse(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret-value-that-is-at-least-32-bytes")
    monkeypatch.setattr(settings, "JWT_ALGORITHM", "HS256")
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "admin@example.com")
    user = make_user()
    raw_token = "refresh-token-" + ("x" * 40)
    record = make_token(
        raw_token,
        user.id,
        "refresh",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    db = AsyncMock()
    db.execute.return_value = result_with_scalar(record)
    db.get.return_value = user
    db.add = Mock()

    first_response = Response()
    first_session = asyncio.run(
        auth.refresh(
            make_request("192.0.2.1", f"basira_refresh={raw_token}"),
            first_response,
            db,
        )
    )
    assert first_session["access_token"]
    assert record.used_at is not None
    refresh_cookie = first_response.headers["set-cookie"]
    assert "basira_refresh=" in refresh_cookie
    assert "httponly" in refresh_cookie.lower()
    rotated_tokens = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], AuthToken) and call.args[0].purpose == "refresh"
    ]
    assert len(rotated_tokens) == 1
    assert rotated_tokens[0].token_hash != record.token_hash

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            auth.refresh(
                make_request("192.0.2.1", f"basira_refresh={raw_token}"),
                Response(),
                db,
            )
        )
    assert error.value.status_code == 401


def test_reset_token_expiry_and_single_use():
    raw_token = "reset-token-" + ("x" * 40)
    user_id = uuid4()
    expired = make_token(
        raw_token,
        user_id,
        "password_reset",
        datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    expired_db = AsyncMock()
    expired_db.execute.return_value = result_with_scalar(expired)
    assert asyncio.run(
        auth._consume_auth_token(expired_db, raw_token, "password_reset")
    ) is None

    reusable = make_token(
        raw_token,
        user_id,
        "password_reset",
        datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    reusable_db = AsyncMock()
    reusable_db.execute.return_value = result_with_scalar(reusable)
    assert asyncio.run(
        auth._consume_auth_token(reusable_db, raw_token, "password_reset")
    ) is reusable
    assert asyncio.run(
        auth._consume_auth_token(reusable_db, raw_token, "password_reset")
    ) is None


def test_registration_ignores_client_admin_role(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "admin@example.com")
    db = AsyncMock()
    db.execute.return_value = result_with_scalar(None)
    db.add = Mock()
    monkeypatch.setattr(auth, "create_auth_token", AsyncMock(return_value="verification-token"))
    background_tasks = BackgroundTasks()

    asyncio.run(
        auth.register(
            auth.RegisterRequest(
                email="new-user@example.com",
                password="a-safe-password",
                full_name="New User",
                role="admin",
            ),
            background_tasks,
            make_request("192.0.2.2"),
            db,
        )
    )

    created_user = db.add.call_args.args[0]
    assert created_user.role == "student"
    assert created_user.email != settings.ADMIN_EMAIL
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is auth._send_auth_link_background


def test_forgot_password_schedules_email_without_sending_inline(monkeypatch):
    user = make_user()
    db = AsyncMock()
    db.execute.return_value = result_with_scalar(user)
    monkeypatch.setattr(auth, "create_auth_token", AsyncMock(return_value="reset-token"))
    background_tasks = BackgroundTasks()

    result = asyncio.run(
        auth.forgot_password(
            auth.ForgotPasswordRequest(email=user.email),
            background_tasks,
            make_request("192.0.2.4"),
            db,
        )
    )

    assert result == auth.FORGOT_RESPONSE
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is auth._send_auth_link_background
    assert background_tasks.tasks[0].args[2] == "password_reset"


def test_resend_email_uses_api_and_logs_only_failure_status(monkeypatch, caplog):
    class FakeResponse:
        is_error = True
        status_code = 429

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout
            self.request = None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            return None

        async def post(self, url, **kwargs):
            self.request = (url, kwargs)
            return FakeResponse()

    clients = []

    def create_client(timeout):
        client = FakeAsyncClient(timeout)
        clients.append(client)
        return client

    monkeypatch.setattr(settings, "RESEND_API_KEY", "sensitive-api-key")
    monkeypatch.setattr(settings, "EMAIL_FROM", "Basira <mail@example.com>")
    monkeypatch.setattr(auth.httpx, "AsyncClient", create_client)

    with pytest.raises(auth.EmailDeliveryError):
        asyncio.run(
            auth.send_auth_email(
                "private-recipient@example.com",
                "Private subject",
                "Private email body",
                "<p>Private email body</p>",
            )
        )

    client = clients[0]
    url, request = client.request
    assert url == "https://api.resend.com/emails"
    assert client.timeout == 10
    assert request["headers"]["Authorization"] == "Bearer sensitive-api-key"
    assert request["json"] == {
        "from": "Basira <mail@example.com>",
        "to": ["private-recipient@example.com"],
        "subject": "Private subject",
        "html": "<p>Private email body</p>",
    }
    assert "status_code=429" in caplog.text
    assert "sensitive-api-key" not in caplog.text
    assert "private-recipient@example.com" not in caplog.text
    assert "Private email body" not in caplog.text


def test_smtp_is_used_when_resend_key_is_missing(monkeypatch):
    send_sync = Mock()
    to_thread = AsyncMock()
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")
    monkeypatch.setattr(auth, "_send_email_sync", send_sync)
    monkeypatch.setattr(auth.asyncio, "to_thread", to_thread)

    asyncio.run(auth.send_auth_email("user@example.com", "Subject", "Body"))

    to_thread.assert_awaited_once_with(send_sync, "user@example.com", "Subject", "Body")


def test_fifth_failed_login_locks_account_for_fifteen_minutes(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(auth, "_verify_password", AsyncMock(return_value=False))
    user = make_user()
    db = AsyncMock()
    db.execute.return_value = result_with_scalar(user)

    errors = []
    for _ in range(auth.FAILED_LOGIN_LIMIT):
        with pytest.raises(HTTPException) as error:
            asyncio.run(
                auth.login(
                    auth.LoginRequest(
                        email=user.email,
                        password="incorrect-password",
                    ),
                    make_request("192.0.2.3"),
                    Response(),
                    db,
                )
            )
        errors.append(error.value.detail)

    assert errors == [auth.LOGIN_ERROR] * auth.FAILED_LOGIN_LIMIT
    assert user.failed_login_attempts == auth.FAILED_LOGIN_LIMIT
    assert user.locked_until is not None
    assert user.locked_until > datetime.now(timezone.utc)
