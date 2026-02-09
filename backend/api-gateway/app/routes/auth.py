from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import httpx
from ..utils.jwt_utils import create_access_token, hash_password, verify_password
from ..config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str
    company_ice: str
    company_rc: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Login endpoint.
    
    For MVP, we use a demo user. In production, verify against database.
    """
    # TODO: In production, verify against auth-service or database
    
    # Demo credentials for testing
    if request.email == "demo@dgi.ma" and request.password == "demo123":
        user_data = {
            "user_id": "demo-001",
            "email": request.email,
            "company_name": "Demo Company",
            "company_ice": "000000000000001"
        }
        
        token = create_access_token({
            "sub": request.email,
            "user_id": user_data["user_id"],
            "company_name": user_data["company_name"],
            "company_ice": user_data["company_ice"]
        })
        
        logger.info(f"User logged in: {request.email}")
        
        return TokenResponse(
            access_token=token,
            user=user_data
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password"
    )


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """
    Register new user.
    
    For MVP, creates token directly. In production, save to database first.
    """
    # TODO: In production:
    # 1. Check if user exists
    # 2. Hash password
    # 3. Save to database
    # 4. Send verification email
    
    # For now, just create token
    user_data = {
        "user_id": f"user-{request.email}",
        "email": request.email,
        "company_name": request.company_name,
        "company_ice": request.company_ice
    }
    
    token = create_access_token({
        "sub": request.email,
        "user_id": user_data["user_id"],
        "company_name": request.company_name,
        "company_ice": request.company_ice
    })
    
    logger.info(f"User registered: {request.email}")
    
    return TokenResponse(
        access_token=token,
        user=user_data
    )


@router.post("/logout")
async def logout():
    """
    Logout endpoint.
    
    With JWT, logout is handled client-side by deleting the token.
    This endpoint is here for completeness and can be used for logging.
    """
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(user = Depends(get_current_user)):
    """Get current user information from token"""
    return user