import asyncio

from argon2 import PasswordHasher, Type
from sqlalchemy import func, select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import User


password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)


async def bootstrap_admin() -> None:
    email = settings.ADMIN_EMAIL.strip().lower()
    password = settings.ADMIN_INITIAL_PASSWORD
    if not email or not password:
        raise RuntimeError("Set ADMIN_EMAIL and ADMIN_INITIAL_PASSWORD in the backend environment.")
    if len(password) < 10:
        raise RuntimeError("ADMIN_INITIAL_PASSWORD must contain at least 10 characters.")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(
                select(User).where(func.lower(User.email) == email)
            )
            user = result.scalar_one_or_none()

            other_admin = await session.execute(
                select(User.id).where(User.role == "admin")
            )
            admin_ids = other_admin.scalars().all()
            has_other_admin = bool(admin_ids) if user is None else any(
                admin_id != user.id for admin_id in admin_ids
            )
            if has_other_admin:
                raise RuntimeError(
                    "Another administrator already exists; remove it before bootstrapping the configured account."
                )

            if user is None:
                user = User(
                    email=email,
                    full_name="Administrator",
                    role="admin",
                    is_active=True,
                    email_verified=True,
                )
                session.add(user)

            user.password_hash = password_hasher.hash(password)
            user.email_verified = True
            user.failed_login_attempts = 0
            user.locked_until = None

    print("Administrator account configured.")


if __name__ == "__main__":
    asyncio.run(bootstrap_admin())
