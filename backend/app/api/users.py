from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.models import User

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get("/me")
async def current_profile(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
    }
