from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBearer
from typing import Any
import structlog

from app.core.database import get_database
from app.services.auth_service import auth_service
from app.services.email_service import email_service
from app.models.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    RefreshTokenRequest,
    EmailVerificationRequest,
)
from app.models.error_responses import (
    get_error_responses,
    get_auth_error_responses,
    get_validation_error_responses,
)
from app.middleware.auth import get_current_user
from app.core.security import verify_token
from app.core.logging import audit_log

logger = structlog.get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email verification",
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "id": "507f1f77bcf86cd799439011",
                        "username": "johndoe",
                        "email": "john@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "is_verified": False,
                        "avatar_url": None,
                        "subscription_plan": "free",
                        "created_at": "2024-01-01T00:00:00Z",
                        "last_login": None,
                    }
                }
            },
        },
        **get_error_responses(400, 409, 422, 500),
    },
)
async def register(user_data: UserCreate, db=Depends(get_database)):
    """Register a new user"""
    try:
        auth_service.set_database(db)

        # Create user
        user = await auth_service.create_user(user_data)

        # Generate email verification token
        verification_token = await auth_service.generate_email_verification_token(
            str(user.id)
        )

        # Send verification email
        await email_service.send_verification_email(
            to_email=user.email,
            username=user.username,
            verification_token=verification_token,
        )

        # Audit log
        audit_log(
            action="user_registered",
            user_id=str(user.id),
            details={"username": user.username, "email": user.email},
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
            last_login=user.last_login,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticate user and return JWT tokens",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        **get_error_responses(400, 401, 403, 422, 429, 500),
    },
)
async def login(login_data: UserLogin, db=Depends(get_database)):
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
            details={"method": "password", "username": user.username},
        )

        logger.info(f"User logged in: {user.username}")
        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
        )


@router.post(
    "/google",
    response_model=Token,
    summary="Google OAuth login",
    description="Authenticate user using Google OAuth token",
    responses={
        200: {
            "description": "Google OAuth login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        **get_error_responses(400, 401, 422, 500),
    },
)
async def google_login(
    token: str = Body(..., embed=True, description="Google ID token"),
    db=Depends(get_database),
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
            details={"method": "google", "username": user.username},
        )

        logger.info(f"Google user logged in: {user.username}")
        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication failed",
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user info",
    description="Get information about the currently authenticated user",
    responses={
        200: {"description": "User information retrieved successfully"},
        **get_auth_error_responses(),
        **get_error_responses(500),
    },
)
async def get_current_user_info(current_user=Depends(get_current_user)):
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
        last_login=current_user.last_login,
    )


@router.post(
    "/logout",
    summary="User logout",
    description="Logout user and invalidate refresh token",
    responses={
        200: {
            "description": "Logout successful",
            "content": {
                "application/json": {"example": {"message": "Successfully logged out"}}
            },
        },
        **get_auth_error_responses(),
        **get_error_responses(500),
    },
)
async def logout(current_user=Depends(get_current_user)):
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
            details={"username": current_user.username},
        )

        logger.info(f"User logged out: {current_user.username}")
        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
    description="Get a new access token using a valid refresh token",
    responses={
        200: {
            "description": "Token refreshed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "token_type": "bearer",
                    }
                }
            },
        },
        **get_error_responses(400, 401, 422, 500),
    },
)
async def refresh_token(token_data: RefreshTokenRequest, db=Depends(get_database)):
    """Refresh access token using refresh token"""
    try:
        auth_service.set_database(db)
        tokens = await auth_service.refresh_tokens(token_data.refresh_token)

        # Audit log
        payload = verify_token(token_data.refresh_token)
        if payload:
            audit_log(
                action="token_refreshed",
                user_id=payload.get("sub", "unknown"),
                details={"refresh_token_used": True},
            )

        logger.info("Access token refreshed successfully")
        return tokens

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post(
    "/verify-email",
    summary="Verify email address",
    description="Verify user's email address using verification token",
    responses={
        200: {
            "description": "Email verified successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Email verified successfully"}
                }
            },
        },
        **get_error_responses(400, 404, 422, 500),
    },
)
async def verify_email(
    verification_data: EmailVerificationRequest, db=Depends(get_database)
):
    """Verify user email with verification token"""
    try:
        auth_service.set_database(db)

        # Verify the email token
        success = await auth_service.verify_email_token(verification_data.token)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Find the user to get details for audit log
        user = await db.users.find_one(
            {"is_verified": True, "email_verification_token": None}, sort=[("_id", -1)]
        )  # Get most recently verified user

        # Send welcome email and audit log
        if user:
            # Send welcome email
            await email_service.send_welcome_email(
                to_email=user["email"], username=user["username"]
            )

            # Audit log
            audit_log(
                action="email_verified",
                user_id=str(user["_id"]),
                details={"email": user["email"]},
            )

        logger.info("Email verified successfully")
        return {"message": "Email verified successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Email verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed",
        )


@router.post(
    "/resend-verification",
    summary="Resend verification email",
    description="Resend email verification token to user's email address",
    responses={
        200: {
            "description": "Verification email sent successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Verification email sent successfully"}
                }
            },
        },
        **get_auth_error_responses(),
        **get_error_responses(400, 422, 500),
    },
)
async def resend_verification_email(
    current_user=Depends(get_current_user), db=Depends(get_database)
):
    """Resend email verification token"""
    try:
        if current_user.is_verified:
            return {"message": "Email already verified"}

        auth_service.set_database(db)

        # Generate new verification token
        token = await auth_service.generate_email_verification_token(
            str(current_user.id)
        )

        # Send verification email
        email_sent = await email_service.send_verification_email(
            to_email=current_user.email,
            username=current_user.username,
            verification_token=token,
        )

        # Audit log
        audit_log(
            action="verification_email_resent",
            user_id=str(current_user.id),
            details={"email": current_user.email},
        )

        logger.info(f"Verification email resent for user: {current_user.username}")

        if email_sent:
            return {"message": "Verification email sent successfully"}
        else:
            return {"message": "Verification email queued (email service unavailable)"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not resend verification email",
        )
