from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
import httpx
import structlog

from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.database import get_database
from app.models.user import UserCreate, UserInDB, UserLogin, Token, GoogleUserInfo
from bson import ObjectId

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self):
        self.db = None

    def set_database(self, db):
        """Set database instance"""
        self.db = db

    def _convert_objectid_to_string(self, user_doc):
        """Convert ObjectId fields to strings for Pydantic compatibility"""
        if user_doc and "_id" in user_doc:
            user_doc["_id"] = str(user_doc["_id"])
        return user_doc

    async def create_user(self, user_data: UserCreate) -> UserInDB:
        """Create a new user"""
        try:
            # Check if user already exists
            existing_user = await self.db.users.find_one(
                {"$or": [{"email": user_data.email}, {"username": user_data.username}]}
            )

            if existing_user:
                if existing_user["email"] == user_data.email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered",
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already taken",
                    )

            # Hash password
            hashed_password = get_password_hash(user_data.password)

            # Create user document
            user_doc = {
                "username": user_data.username,
                "email": user_data.email,
                "full_name": user_data.full_name,
                "hashed_password": hashed_password,
                "is_active": True,
                "is_verified": False,
                "subscription_plan": "free",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "failed_login_attempts": 0,
            }

            # Insert user
            result = await self.db.users.insert_one(user_doc)
            user_doc["_id"] = str(result.inserted_id)

            logger.info(f"User created successfully: {user_data.username}")
            return UserInDB(**user_doc)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create user",
            )

    async def authenticate_user(self, login_data: UserLogin) -> Optional[UserInDB]:
        """Authenticate user with username/email and password"""
        try:
            # Find user by username or email
            user_doc = await self.db.users.find_one(
                {
                    "$or": [
                        {"username": login_data.username_or_email},
                        {"email": login_data.username_or_email},
                    ]
                }
            )

            if not user_doc:
                logger.warning(
                    f"Login attempt for non-existent user: {login_data.username_or_email}"
                )
                return None

            user_doc = self._convert_objectid_to_string(user_doc)
            user = UserInDB(**user_doc)

            # Check if account is locked
            if user.locked_until and user.locked_until > datetime.utcnow():
                logger.warning(f"Login attempt for locked account: {user.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is temporarily locked due to too many failed attempts",
                )

            # Verify password
            if not verify_password(login_data.password, user.hashed_password):
                # Increment failed attempts
                await self._handle_failed_login(user.id)
                logger.warning(f"Failed login attempt for user: {user.username}")
                return None

            # Reset failed attempts on successful login
            if user.failed_login_attempts > 0:
                await self.db.users.update_one(
                    {"_id": ObjectId(user.id)},
                    {
                        "$set": {
                            "failed_login_attempts": 0,
                            "locked_until": None,
                            "last_login": datetime.utcnow(),
                        }
                    },
                )
            else:
                # Just update last login
                await self.db.users.update_one(
                    {"_id": ObjectId(user.id)},
                    {"$set": {"last_login": datetime.utcnow()}},
                )

            logger.info(f"User authenticated successfully: {user.username}")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    async def _handle_failed_login(self, user_id: str):
        """Handle failed login attempt"""
        try:
            user_doc = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                return

            failed_attempts = user_doc.get("failed_login_attempts", 0) + 1
            update_data = {"failed_login_attempts": failed_attempts}

            # Lock account after 5 failed attempts
            if failed_attempts >= 5:
                lock_duration = timedelta(minutes=30)  # 30 minutes lock
                update_data["locked_until"] = datetime.utcnow() + lock_duration
                logger.warning(
                    f"Account locked for user {user_id} due to {failed_attempts} failed attempts"
                )

            await self.db.users.update_one(
                {"_id": ObjectId(user_id)}, {"$set": update_data}
            )

        except Exception as e:
            logger.error(f"Error handling failed login: {e}")

    async def get_user_by_id(self, user_id: str) -> Optional[UserInDB]:
        """Get user by ID"""
        try:
            user_doc = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if not user_doc:
                return None
            
            user_doc = self._convert_objectid_to_string(user_doc)
            return UserInDB(**user_doc)
            
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    async def create_tokens(self, user: UserInDB) -> Token:
        """Create access and refresh tokens for user"""
        try:
            access_token_expires = timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

            token_data = {
                "sub": str(user.id),
                "username": user.username,
                "email": user.email,
            }

            access_token = create_access_token(
                data=token_data, expires_delta=access_token_expires
            )

            refresh_token = create_refresh_token(data=token_data)

            return Token(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )

        except Exception as e:
            logger.error(f"Error creating tokens: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create authentication tokens",
            )

    async def refresh_tokens(self, refresh_token: str) -> Token:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = verify_token(refresh_token)
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )

            # Check if it's actually a refresh token
            if payload.get("type") != "refresh_token":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type",
                )

            # Get user from database
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )

            user = await self.get_user_by_id(user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            # Create new tokens
            return await self.create_tokens(user)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error refreshing tokens: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not refresh tokens",
            )

    async def generate_email_verification_token(self, user_id: str) -> str:
        """Generate email verification token for user"""
        try:
            import secrets
            from datetime import datetime, timedelta
            
            # Generate secure random token
            token = secrets.token_urlsafe(32)
            expires = datetime.utcnow() + timedelta(hours=24)  # 24 hour expiry
            
            # Update user with verification token
            await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "email_verification_token": token,
                        "email_verification_expires": expires,
                    }
                }
            )
            
            return token
            
        except Exception as e:
            logger.error(f"Error generating email verification token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate verification token",
            )

    async def verify_email_token(self, token: str) -> bool:
        """Verify email verification token and mark user as verified"""
        try:
            from datetime import datetime
            
            # Find user with this token
            user = await self.db.users.find_one({
                "email_verification_token": token,
                "email_verification_expires": {"$gt": datetime.utcnow()}
            })
            
            if not user:
                return False
            
            # Mark user as verified and clear verification token
            await self.db.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "is_verified": True,
                        "email_verification_token": None,
                        "email_verification_expires": None,
                    }
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying email token: {e}")
            # Return False instead of raising exception to indicate invalid token
            return False

    async def google_login(self, token: str) -> UserInDB:
        """Authenticate user with Google OAuth token"""
        try:
            # Verify Google token
            if not settings.GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google OAuth not configured",
                )

            # Verify the token with Google
            try:
                idinfo = id_token.verify_oauth2_token(
                    token, requests.Request(), settings.GOOGLE_CLIENT_ID
                )

                if idinfo["iss"] not in [
                    "accounts.google.com",
                    "https://accounts.google.com",
                ]:
                    raise ValueError("Wrong issuer.")

                google_user = GoogleUserInfo(
                    id=idinfo["sub"],
                    email=idinfo["email"],
                    name=idinfo.get("name", ""),
                    picture=idinfo.get("picture"),
                    verified_email=idinfo.get("email_verified", False),
                )

            except ValueError as e:
                logger.warning(f"Invalid Google token: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Google token",
                )

            # Check if user exists with this Google ID
            user_doc = await self.db.users.find_one({"google_id": google_user.id})

            if user_doc:
                # Update last login
                await self.db.users.update_one(
                    {"_id": user_doc["_id"]},
                    {"$set": {"last_login": datetime.utcnow()}},
                )
                user_doc = self._convert_objectid_to_string(user_doc)
                user = UserInDB(**user_doc)
                logger.info(f"Google user logged in: {user.username}")
                return user

            # Check if user exists with this email
            user_doc = await self.db.users.find_one({"email": google_user.email})

            if user_doc:
                # Link Google account to existing user
                await self.db.users.update_one(
                    {"_id": user_doc["_id"]},
                    {
                        "$set": {
                            "google_id": google_user.id,
                            "avatar_url": google_user.picture,
                            "is_verified": True,  # Google emails are verified
                            "last_login": datetime.utcnow(),
                        }
                    },
                )
                user_doc["google_id"] = google_user.id
                user_doc["avatar_url"] = google_user.picture
                user_doc["is_verified"] = True

                user_doc = self._convert_objectid_to_string(user_doc)
                user = UserInDB(**user_doc)
                logger.info(f"Google account linked to existing user: {user.username}")
                return user

            # Create new user from Google account
            username = google_user.email.split("@")[0]
            # Ensure username is unique
            counter = 1
            original_username = username
            while await self.db.users.find_one({"username": username}):
                username = f"{original_username}{counter}"
                counter += 1

            user_doc = {
                "username": username,
                "email": google_user.email,
                "full_name": google_user.name,
                "google_id": google_user.id,
                "avatar_url": google_user.picture,
                "hashed_password": "",  # No password for Google users
                "is_active": True,
                "is_verified": True,  # Google emails are verified
                "subscription_plan": "free",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "last_login": datetime.utcnow(),
                "failed_login_attempts": 0,
            }

            result = await self.db.users.insert_one(user_doc)
            user_doc["_id"] = str(result.inserted_id)

            user_doc = self._convert_objectid_to_string(user_doc)
            user = UserInDB(**user_doc)
            logger.info(f"New Google user created: {user.username}")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error with Google login: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google authentication failed",
            )


# Global auth service instance
auth_service = AuthService()
