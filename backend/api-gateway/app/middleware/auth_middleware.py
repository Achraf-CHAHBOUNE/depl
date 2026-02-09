from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict
from ..utils.jwt_utils import verify_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    Extract and verify user from JWT token.
    Use this as a dependency in protected routes.
    
    Example:
        @router.get("/protected")
        async def protected_route(user = Depends(get_current_user)):
            return {"user_id": user["user_id"]}
    """
    token = credentials.credentials
    
    try:
        payload = verify_token(token)
        
        # Extract user info
        user_id = payload.get("user_id")
        email = payload.get("sub")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        return {
            "user_id": user_id,
            "email": email,
            "company_name": payload.get("company_name"),
            "company_ice": payload.get("company_ice"),
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Optional authentication - returns None if no token"""
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None