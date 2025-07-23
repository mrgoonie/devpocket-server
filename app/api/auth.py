from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer
from typing import Any
import structlog

from app.core.database import get_database
from app.services.auth_service import auth_service
from app.models.user import UserCreate, UserLogin, UserResponse, Token
from app.middleware.auth import get_current_user
from app.core.logging import audit_log

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db=Depends(get_database)
):
    """Register a new user"""
    try:
        auth_service.set_database(db)
        
        # Create user
        user = await auth_service.create_user(user_data)
        
        # Audit log
        audit_log(
            action="user_registered",
            user_id=str(user.id),
            details={"username": user.username, "email": user.email}
        )
        
        # Return user response (exclude sensitive data)
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_verified=user.is_verified,
            avatar_url=user.avatar_url,
            subscription_plan=user.subscription_plan,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db=Depends(get_database)
):
    """Login with username/email and password"""
    try:
        auth_service.set_database(db)
        
        # Authenticate user
        user = await auth_service.authenticate_user(login_data)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create tokens
        tokens = await auth_service.create_tokens(user)
        
        # Audit log
        audit_log(
            action="user_login",
            user_id=str(user.id),
            details={"method": "password", "username": user.username}
        )
        
        logger.info(f"User logged in: {user.username}")
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/google", response_model=Token)
async def google_login(
    token: str = Body(..., embed=True, description="Google ID token"),
    db=Depends(get_database)
):
    """Login with Google OAuth token"""
    try:
        auth_service.set_database(db)
        
        # Authenticate with Google
        user = await auth_service.google_login(token)
        
        # Create tokens
        tokens = await auth_service.create_tokens(user)
        
        # Audit log
        audit_log(
            action="user_login",
            user_id=str(user.id),
            details={"method": "google", "username": user.username}
        )
        
        logger.info(f"Google user logged in: {user.username}")
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user=Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        avatar_url=current_user.avatar_url,
        subscription_plan=current_user.subscription_plan,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@router.post("/logout")
async def logout(
    current_user=Depends(get_current_user)
):
    """Logout current user"""
    try:
        # In a real implementation, you might:
        # 1. Add token to blacklist
        # 2. Clear session data
        # 3. Log the logout event
        
        # Audit log
        audit_log(
            action="user_logout",
            user_id=str(current_user.id),
            details={"username": current_user.username}
        )
        
        logger.info(f"User logged out: {current_user.username}")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@router.post("/verify-email")
async def verify_email(
    current_user=Depends(get_current_user),
    db=Depends(get_database)
):
    """Verify user email (simplified - in real app would need email verification flow)"""
    try:
        if current_user.is_verified:
            return {"message": "Email already verified"}
        
        # Update user verification status
        await db.users.update_one(
            {"_id": current_user.id},
            {"$set": {"is_verified": True}}
        )
        
        # Audit log
        audit_log(
            action="email_verified",
            user_id=str(current_user.id),
            details={"email": current_user.email}
        )
        
        logger.info(f"Email verified for user: {current_user.username}")
        return {"message": "Email verified successfully"}
        
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )