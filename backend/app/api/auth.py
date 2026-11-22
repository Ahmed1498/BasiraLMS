import asyncio
import hashlib
import hmac
import logging
import secrets
import smtplib
import ssl
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import quote

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from jose import jwt
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import verify_supabase_jwt
from app.models.models import AuthToken, User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 7
RESET_TOKEN_MINUTES = 30
VERIFY_TOKEN_HOURS = 24
FAILED_LOGIN_LIMIT = 5
ACCOUNT_LOCK_MINUTES = 15
REFRESH_COOKIE_NAME = "basira_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
LOGIN_ERROR = "Invalid email or password"
FORGOT_RESPONSE = {
    "message": "If an account exists for this email, password recovery instructions have been sent."
}

password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)
_dummy_password_hash = password_hasher.hash(secrets.token_urlsafe(32))
_auth_rate_limits: dict[tuple[str, str, str], deque[float]] = defaultdict(deque)


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    role: str = "student"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Full name must contain at least 2 characters")
        return normalized


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized


class ForgotPasswordRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized


class VerifyEmailRequest(BaseModel):
    token: str | None = None
    token_hash: str | None = None

    @model_validator(mode="after")
    def require_token(self):
        if not (self.token or self.token_hash):
            raise ValueError("A verification token is required")
        return self


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=10, max_length=128)


class EmailDeliveryError(Exception):
    pass


def _configured_admin_email() -> str:
    email = settings.ADMIN_EMAIL.strip().lower()
    if not email:
        raise HTTPException(status_code=503, detail="ADMIN_EMAIL is not configured")
    return email


def _jwt_secret() -> str:
    secret = settings.JWT_SECRET
    if len(secret.encode("utf-8")) < 32 or settings.JWT_ALGORITHM != "HS256":
        raise HTTPException(
            status_code=503,
            detail="JWT_SECRET must be at least 32 bytes and JWT_ALGORITHM must be HS256",
        )
    return secret


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=REFRESH_TOKEN_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=settings.FRONTEND_URL.lower().startswith("https://"),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.FRONTEND_URL.lower().startswith("https://"),
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


def _dashboard_for(user: User) -> str:
    return "/admin/dashboard" if user.role == "admin" else f"/{user.role}/dashboard"


def _session_response(user: User, refresh_token: str, response: Response) -> dict:
    _set_refresh_cookie(response, refresh_token)
    return {
        "access_token": _access_token(user),
        "token_type": "bearer",
        "role": user.role,
        "dashboard": _dashboard_for(user),
    }


def _apply_rate_limit(
    action: str,
    request: Request,
    identity: str,
    limit: int,
    window_seconds: int,
) -> None:
    client_host = request.client.host if request.client else "unknown"
    key = (action, client_host, identity)
    now = time.monotonic()
    timestamps = _auth_rate_limits[key]
    while timestamps and now - timestamps[0] >= window_seconds:
        timestamps.popleft()
    if len(timestamps) >= limit:
        retry_after = max(1, int(window_seconds - (now - timestamps[0])))
        raise HTTPException(
            status_code=429,
            detail="Too many authentication attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )
    timestamps.append(now)


def _frontend_link(path: str, token: str) -> str:
    base_url = settings.FRONTEND_URL.strip().rstrip("/")
    if not base_url:
        raise EmailDeliveryError("FRONTEND_URL is not configured")
    return f"{base_url}{path}#token={quote(token, safe='')}"


def _send_email_sync(recipient: str, subject: str, body: str) -> None:
    missing = [
        name
        for name, value in (
            ("SMTP_HOST", settings.SMTP_HOST),
            ("SMTP_USERNAME", settings.SMTP_USERNAME),
            ("SMTP_PASSWORD", settings.SMTP_PASSWORD),
            ("SMTP_FROM_EMAIL", settings.SMTP_FROM_EMAIL),
        )
        if not value
    ]
    if missing:
        raise EmailDeliveryError("SMTP settings are incomplete")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = recipient
    message.set_content(body)

    phase = "connect"
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
            phase = "ehlo"
            server.ehlo()
            phase = "starttls"
            server.starttls(context=ssl.create_default_context())
            phase = "ehlo_after_tls"
            server.ehlo()
            phase = "login"
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            phase = "send_message"
            server.send_message(message)
            phase = "quit"
    except (OSError, smtplib.SMTPException, TimeoutError) as exc:
        raise EmailDeliveryError(
            f"SMTP failed during {phase} ({type(exc).__name__})"
        ) from exc


async def send_auth_email(recipient: str, subject: str, body: str) -> None:
    try:
        await asyncio.to_thread(_send_email_sync, recipient, subject, body)
    except EmailDeliveryError as exc:
        logger.error(
            "Authentication email delivery failed; reason=%s",
            exc,
        )
        raise EmailDeliveryError from exc
    except (OSError, smtplib.SMTPException, TimeoutError) as exc:
        logger.error(
            "Authentication email delivery failed; phase=unknown exception_type=%s",
            type(exc).__name__,
        )
        raise EmailDeliveryError from exc


async def create_auth_token(
    db: AsyncSession,
    user: User,
    purpose: str,
    lifetime: timedelta,
) -> str:
    raw_token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            token_hash=_hash_token(raw_token),
            user_id=user.id,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + lifetime,
        )
    )
    await db.flush()
    return raw_token


async def send_auth_link(user: User, token: str, purpose: str) -> None:
    if purpose == "verify_email":
        path = "/login"
        subject = "Confirm your Basira LMS email"
        action = "confirm your email address"
    elif purpose == "password_reset":
        path = "/reset-password"
        subject = "Set or reset your Basira LMS password"
        action = "set a new password"
    else:
        raise ValueError("Unsupported authentication email purpose")
    link = _frontend_link(path, token)
    await send_auth_email(
        user.email,
        subject,
        f"Use this link to {action}:\n\n{link}\n\nIf you did not request this, ignore this email.",
    )


async def _consume_auth_token(
    db: AsyncSession,
    raw_token: str,
    purpose: str,
) -> AuthToken | None:
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(AuthToken)
        .where(
            AuthToken.token_hash == token_hash,
            AuthToken.purpose == purpose,
        )
        .with_for_update()
    )
    record = result.scalar_one_or_none()
    if record is None or not hmac.compare_digest(record.token_hash, token_hash):
        return None
    now = datetime.now(timezone.utc)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if record.used_at is not None or expires_at <= now:
        return None
    record.used_at = now
    await db.flush()
    return record


def _verify_password_sync(stored_hash: str | None, password: str) -> bool:
    if not stored_hash:
        try:
            password_hasher.verify(_dummy_password_hash, password)
        except VerificationError:
            pass
        return False
    try:
        return password_hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


async def _verify_password(stored_hash: str | None, password: str) -> bool:
    return await asyncio.to_thread(_verify_password_sync, stored_hash, password)


def _raise_invalid_login() -> None:
    raise HTTPException(status_code=401, detail=LOGIN_ERROR)


@router.post("/signup", status_code=201)
@router.post("/register", status_code=201)
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _apply_rate_limit("register", request, "", limit=5, window_seconds=3600)
    if data.email == _configured_admin_email():
        raise HTTPException(status_code=403, detail="This email is reserved for the administrator")

    result = await db.execute(
        select(User).where(func.lower(User.email) == data.email)
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    role = data.role if data.role in {"student", "teacher"} else "student"
    user = User(
        email=data.email,
        full_name=data.full_name,
        role=role,
        is_active=True,
        password_hash=await asyncio.to_thread(password_hasher.hash, data.password),
        email_verified=False,
    )
    db.add(user)
    await db.flush()
    token = await create_auth_token(
        db,
        user,
        purpose="verify_email",
        lifetime=timedelta(hours=VERIFY_TOKEN_HOURS),
    )
    try:
        await send_auth_link(user, token, "verify_email")
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not send the verification email. Check the SMTP configuration.",
        ) from exc
    return {"message": "Account created. Check your email to verify it."}


signup = register


@router.post("/login")
async def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    _apply_rate_limit("login", request, "", limit=10, window_seconds=60)
    admin_email = _configured_admin_email()
    result = await db.execute(
        select(User)
        .where(func.lower(User.email) == data.email)
        .with_for_update()
    )
    user = result.scalar_one_or_none()
    if user is None:
        await _verify_password(None, data.password)
        _raise_invalid_login()

    now = datetime.now(timezone.utc)
    if user.locked_until is not None:
        locked_until = user.locked_until
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            await _verify_password(None, data.password)
            _raise_invalid_login()
        user.locked_until = None
        user.failed_login_attempts = 0

    password_valid = await _verify_password(user.password_hash, data.password)
    if not password_valid:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= FAILED_LOGIN_LIMIT:
            user.locked_until = now + timedelta(minutes=ACCOUNT_LOCK_MINUTES)
        await db.commit()
        _raise_invalid_login()

    if (
        not user.is_active
        or not user.email_verified
        or (user.role == "admin" and user.email.lower() != admin_email)
        or (user.email.lower() == admin_email and user.role != "admin")
    ):
        _raise_invalid_login()

    user.failed_login_attempts = 0
    user.locked_until = None
    refresh_token = await create_auth_token(
        db,
        user,
        purpose="refresh",
        lifetime=timedelta(days=REFRESH_TOKEN_DAYS),
    )
    return _session_response(user, refresh_token, response)


@router.post("/verify-email")
@router.post("/confirm", include_in_schema=False)
async def verify_email(
    data: VerifyEmailRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    record = await _consume_auth_token(
        db,
        data.token or data.token_hash or "",
        purpose="verify_email",
    )
    if record is None:
        raise HTTPException(status_code=400, detail="Verification link is invalid, expired, or already used")
    user = await db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Verification link is invalid, expired, or already used")

    admin_email = _configured_admin_email()
    if user.role == "admin" and user.email.lower() != admin_email:
        raise HTTPException(status_code=403, detail="Administrator account is not permitted")
    user.email_verified = True
    refresh_token = await create_auth_token(
        db,
        user,
        purpose="refresh",
        lifetime=timedelta(days=REFRESH_TOKEN_DAYS),
    )
    return _session_response(user, refresh_token, response)


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    _apply_rate_limit("forgot-password", request, "", limit=3, window_seconds=3600)
    result = await db.execute(
        select(User).where(func.lower(User.email) == data.email)
    )
    user = result.scalar_one_or_none()
    if user is not None and user.is_active:
        token = await create_auth_token(
            db,
            user,
            purpose="password_reset",
            lifetime=timedelta(minutes=RESET_TOKEN_MINUTES),
        )
        try:
            await send_auth_link(user, token, "password_reset")
        except EmailDeliveryError:
            token_hash = _hash_token(token)
            token_result = await db.execute(
                select(AuthToken).where(AuthToken.token_hash == token_hash)
            )
            token_record = token_result.scalar_one_or_none()
            if token_record is not None:
                token_record.used_at = datetime.now(timezone.utc)
    return FORGOT_RESPONSE


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    record = await _consume_auth_token(
        db,
        data.token,
        purpose="password_reset",
    )
    if record is None:
        raise HTTPException(status_code=400, detail="Reset link is invalid, expired, or already used")
    user = await db.get(User, record.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Reset link is invalid, expired, or already used")
    user.password_hash = await asyncio.to_thread(password_hasher.hash, data.password)
    user.email_verified = True
    user.failed_login_attempts = 0
    user.locked_until = None

    result = await db.execute(
        select(AuthToken).where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == "refresh",
            AuthToken.used_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for refresh_token in result.scalars().all():
        refresh_token.used_at = now
    return {"message": "Password updated. Sign in with your new password."}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_token:
        raise HTTPException(status_code=401, detail="Refresh session is missing or expired")
    record = await _consume_auth_token(db, raw_token, purpose="refresh")
    if record is None:
        raise HTTPException(status_code=401, detail="Refresh session is missing or expired")
    user = await db.get(User, record.user_id)
    admin_email = _configured_admin_email()
    if (
        user is None
        or not user.is_active
        or not user.email_verified
        or (user.role == "admin" and user.email.lower() != admin_email)
        or (user.email.lower() == admin_email and user.role != "admin")
    ):
        raise HTTPException(status_code=401, detail="Refresh session is missing or expired")

    next_refresh_token = await create_auth_token(
        db,
        user,
        purpose="refresh",
        lifetime=timedelta(days=REFRESH_TOKEN_DAYS),
    )
    _set_refresh_cookie(response, next_refresh_token)
    return {
        "access_token": _access_token(user),
        "token_type": "bearer",
        "role": user.role,
        "dashboard": _dashboard_for(user),
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_token:
        await _consume_auth_token(db, raw_token, purpose="refresh")
    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully."}


@router.post("/admin/bootstrap")
async def disabled_admin_bootstrap():
    raise HTTPException(
        status_code=410,
        detail="Create the administrator using the backend bootstrap_admin.py script.",
    )


@router.get("/me")
async def auth_me(
    payload: dict = Depends(verify_supabase_jwt),
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=401, detail="Invalid user identifier") from exc
    user = await db.get(User, user_id)
    if user is None or not user.is_active or not user.email_verified:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    admin_email = _configured_admin_email()
    if user.role == "admin" and user.email.lower() != admin_email:
        raise HTTPException(status_code=403, detail="Administrator access is not permitted")
    if user.email.lower() == admin_email and user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator account is not configured")
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "dashboard": _dashboard_for(user),
        "is_active": user.is_active,
    }
