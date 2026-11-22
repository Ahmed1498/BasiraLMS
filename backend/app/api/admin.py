from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import EmailDeliveryError, create_auth_token, send_auth_link
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_role
from app.models.models import Course, Submission, User
from app.schemas.api import UserInvite, UserUpdate

router = APIRouter(prefix="/api/v1/admin", tags=["Administration"])


@router.get("/overview")
async def admin_overview(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(["admin"])),
):
    user_count = await db.scalar(select(func.count()).select_from(User))
    course_count = await db.scalar(select(func.count()).select_from(Course))
    pending_count = await db.scalar(
        select(func.count()).select_from(Submission).where(Submission.status == "submitted")
    )
    return {
        "user_count": user_count or 0,
        "course_count": course_count or 0,
        "pending_submissions": pending_count or 0,
    }


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(["admin"])),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return {
        "users": [
            {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
            for user in result.scalars().all()
        ]
    }


@router.post("/users/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    data: UserInvite,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(["admin"])),
):
    email = data.email.strip().lower()
    admin_email = settings.ADMIN_EMAIL.strip().lower()
    if not admin_email:
        raise HTTPException(status_code=503, detail="ADMIN_EMAIL is not configured")
    if email == admin_email:
        raise HTTPException(status_code=403, detail="This email is reserved for the administrator")
    existing = await db.execute(select(User.id).where(func.lower(User.email) == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    profile = User(
        email=email,
        full_name=data.full_name,
        role=data.role,
        is_active=True,
        password_hash=None,
        email_verified=False,
    )
    db.add(profile)
    await db.flush()
    token = await create_auth_token(
        db,
        profile,
        purpose="password_reset",
        lifetime=timedelta(minutes=30),
    )
    try:
        await send_auth_link(profile, token, "password_reset")
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not send the invitation email. Check the SMTP configuration.",
        ) from exc
    return {"id": str(profile.id), "email": profile.email, "role": profile.role}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role(["admin"])),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and data.role is not None and data.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own administrator role")
    if user.id == admin.id and data.is_active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    if data.role == "admin" and user.email.lower() != settings.ADMIN_EMAIL.lower():
        raise HTTPException(
            status_code=403,
            detail="Only the configured administrator account can have the administrator role",
        )
    if user.email.lower() == settings.ADMIN_EMAIL.lower() and data.role not in {None, "admin"}:
        raise HTTPException(
            status_code=400,
            detail="The configured administrator account must retain its administrator role",
        )

    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    await db.flush()
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }
