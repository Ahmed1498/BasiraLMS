import time
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User

security = HTTPBearer()
ai_rate_limit_store: dict[str, list[float]] = {}


async def verify_supabase_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    if len(settings.JWT_SECRET.encode("utf-8")) < 32 or settings.JWT_ALGORITHM != "HS256":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT_SECRET must be at least 32 bytes and JWT_ALGORITHM must be HS256",
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            options={
                "verify_aud": False,
                "verify_exp": True,
                "verify_signature": True,
            },
        )
        UUID(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access" or "exp" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_current_user(
    payload: dict = Depends(verify_supabase_jwt),
    db: AsyncSession = Depends(get_db),
) -> User:
    user_id = UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    admin_email = settings.ADMIN_EMAIL.strip().lower()
    if user.role == "admin" and user.email.lower() != admin_email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is not permitted",
        )
    if user.email.lower() == admin_email and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator account is not configured",
        )
    if not user.is_active or not user.email_verified:
        raise HTTPException(status_code=403, detail="This account is inactive or unverified")
    return user


def require_role(allowed_roles: list[str]):
    async def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role == "admin" and user.email.lower() != settings.ADMIN_EMAIL.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator access is restricted to the configured administrator account",
            )
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {allowed_roles}",
            )
        return user

    return role_dependency


async def enforce_ai_rate_limit(
    user: User = Depends(require_role(["student"])),
):
    current_time = time.time()
    window_size = 3600
    max_requests = 20

    user_id = str(user.id)
    user_requests = ai_rate_limit_store.get(user_id, [])
    user_requests = [
        timestamp
        for timestamp in user_requests
        if current_time - timestamp < window_size
    ]

    if len(user_requests) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI request limit reached. Try again later.",
        )

    user_requests.append(current_time)
    ai_rate_limit_store[user_id] = user_requests
