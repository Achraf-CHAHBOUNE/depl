from fastapi import APIRouter, Depends
from ..middleware.auth_middleware import get_current_user

router = APIRouter()


@router.get("/me")
async def get_current_user_profile(user = Depends(get_current_user)):
    """Get current user profile"""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "company_name": user.get("company_name"),
        "company_ice": user.get("company_ice")
    }


@router.put("/me")
async def update_profile(
    update_data: dict,
    user = Depends(get_current_user)
):
    """Update user profile"""
    # TODO: Implement profile updates
    return {"message": "Profile updated", "data": update_data}