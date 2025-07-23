from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import verify_token
from app.core.database import get_database
from app.models.user import UserInDB
from bson import ObjectId
from typing import Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)
security = HTTPBearer()

def _convert_objectid_to_string(user_doc):
    """Convert ObjectId fields to strings for Pydantic compatibility"""
    if user_doc and "_id" in user_doc:
        user_doc["_id"] = str(user_doc["_id"])
    return user_doc

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_database)
) -> UserInDB:
    """Get current authenticated user from JWT token"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        if payload is None:
            logger.warning("Invalid token provided")
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            logger.warning("Token missing user ID")
            raise credentials_exception
            
        # Get user from database
        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc is None:
            logger.warning(f"User not found: {user_id}")
            raise credentials_exception
            
        user_doc = _convert_objectid_to_string(user_doc)
        user = UserInDB(**user_doc)
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Inactive user attempted access: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            logger.warning(f"Locked user attempted access: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is temporarily locked"
            )
            
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in authentication: {e}")
        raise credentials_exception

async def get_current_verified_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """Get current user if verified"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address"
        )
    return current_user

async def get_current_admin_user(
    current_user: UserInDB = Depends(get_current_verified_user)
) -> UserInDB:
    """Get current user if admin (pro subscription or admin role)"""
    if current_user.subscription_plan not in ["pro", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Convenient aliases
get_current_active_user = get_current_user
require_admin = get_current_admin_user

class OptionalAuth:
    """Optional authentication dependency"""
    
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)
    
    async def __call__(
        self, 
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        db=Depends(get_database)
    ) -> Optional[UserInDB]:
        
        if credentials is None:
            return None
            
        try:
            payload = verify_token(credentials.credentials)
            if payload is None:
                return None
                
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
                
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
            if user_doc is None:
                return None
                
            user_doc = _convert_objectid_to_string(user_doc)
            user = UserInDB(**user_doc)
            return user if user.is_active else None
            
        except Exception:
            return None

optional_auth = OptionalAuth()