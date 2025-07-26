import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access_token"})

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token",
        )


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )

        # Check if token is expired
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
            return None

        return payload

    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}")
        return None


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create JWT refresh token (longer expiry)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh_token"})

    try:
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create refresh token",
        )


def generate_api_key() -> str:
    """Generate a secure API key for external integrations"""
    import secrets

    return f"dpk_{secrets.token_urlsafe(32)}"


class SecurityHeaders:
    """Security headers for API responses"""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self' https://cdn.jsdelivr.net https://fastapi.tiangolo.com https://fonts.googleapis.com https://fonts.gstatic.com blob:; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net blob:; img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; font-src 'self' https://fonts.gstatic.com; worker-src 'self' blob:;",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
