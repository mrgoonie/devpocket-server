"""Tests for middleware auth module."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.middleware.auth import (
    OptionalAuth,
    _convert_objectid_to_string,
    get_current_admin_user,
    get_current_user,
    get_current_verified_user,
    optional_auth,
)
from app.models.user import UserInDB


class TestConvertObjectId:
    """Test ObjectId conversion utility."""

    def test_convert_objectid_to_string(self):
        """Test converting ObjectId to string."""
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "email": "test@example.com",
        }

        result = _convert_objectid_to_string(user_doc)

        assert isinstance(result["_id"], str)
        assert result["_id"] == "507f1f77bcf86cd799439011"
        assert result["username"] == "testuser"
        assert result["email"] == "test@example.com"

    def test_convert_objectid_none_doc(self):
        """Test converting None document."""
        result = _convert_objectid_to_string(None)
        assert result is None

    def test_convert_objectid_no_id_field(self):
        """Test converting document without _id field."""
        user_doc = {"username": "testuser", "email": "test@example.com"}

        result = _convert_objectid_to_string(user_doc)

        assert result == user_doc  # Should return unchanged


class TestGetCurrentUser:
    """Test get_current_user function."""

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_get_current_user_success(self, mock_verify_token):
        """Test successful user authentication."""
        # Setup mocks
        user_id = "507f1f77bcf86cd799439011"
        mock_verify_token.return_value = {"sub": user_id}

        mock_db = MagicMock()
        mock_collection = AsyncMock()
        user_doc = {
            "_id": ObjectId(user_id),
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "hashed_password_value",
            "subscription_plan": "free",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.now(timezone.utc),
        }
        mock_collection.find_one.return_value = user_doc
        mock_db.users = mock_collection

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        result = await get_current_user(credentials, mock_db)

        assert isinstance(result, UserInDB)
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        mock_verify_token.assert_called_once_with("valid_token")
        mock_collection.find_one.assert_called_once_with({"_id": ObjectId(user_id)})

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_get_current_user_invalid_token(self, mock_verify_token):
        """Test authentication with invalid token."""
        mock_verify_token.return_value = None
        mock_db = MagicMock()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, mock_db)

        assert exc_info.value.status_code == 401
        assert "Could not validate credentials" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_get_current_user_no_user_id(self, mock_verify_token):
        """Test authentication with token missing user ID."""
        mock_verify_token.return_value = {"other_field": "value"}
        mock_db = MagicMock()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="token_no_user_id"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_get_current_user_not_found(self, mock_verify_token):
        """Test authentication with user not found in database."""
        user_id = "507f1f77bcf86cd799439011"
        mock_verify_token.return_value = {"sub": user_id}

        mock_db = MagicMock()
        mock_collection = AsyncMock()
        mock_collection.find_one.return_value = None
        mock_db.users = mock_collection

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, mock_db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_get_current_user_inactive(self, mock_verify_token):
        """Test authentication with inactive user."""
        user_id = "507f1f77bcf86cd799439011"
        mock_verify_token.return_value = {"sub": user_id}

        mock_db = MagicMock()
        mock_collection = AsyncMock()
        user_doc = {
            "_id": ObjectId(user_id),
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "subscription_plan": "free",
            "hashed_password": "hashed_password_value",
            "is_active": False,  # Inactive user
            "is_verified": True,
            "created_at": datetime.now(timezone.utc),
        }
        mock_collection.find_one.return_value = user_doc
        mock_db.users = mock_collection

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, mock_db)

        assert exc_info.value.status_code == 401
        assert "Inactive user" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_get_current_user_locked(self, mock_verify_token):
        """Test authentication with locked user."""
        user_id = "507f1f77bcf86cd799439011"
        mock_verify_token.return_value = {"sub": user_id}

        mock_db = MagicMock()
        mock_collection = AsyncMock()
        user_doc = {
            "_id": ObjectId(user_id),
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "subscription_plan": "free",
            "hashed_password": "hashed_password_value",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.now(timezone.utc),
            "locked_until": datetime.now(timezone.utc) + timedelta(hours=1),  # Locked
        }
        mock_collection.find_one.return_value = user_doc
        mock_db.users = mock_collection

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, mock_db)

        assert exc_info.value.status_code == 401
        assert "Account is temporarily locked" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_get_current_user_exception(self, mock_verify_token):
        """Test authentication with unexpected exception."""
        mock_verify_token.side_effect = Exception("Unexpected error")
        mock_db = MagicMock()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, mock_db)

        assert exc_info.value.status_code == 401


class TestGetCurrentVerifiedUser:
    """Test get_current_verified_user function."""

    @pytest.mark.asyncio
    async def test_get_current_verified_user_success(self):
        """Test getting verified user."""
        user = UserInDB(
            id="507f1f77bcf86cd799439011",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_password_value",
            subscription_plan="free",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
        )

        result = await get_current_verified_user(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_get_current_verified_user_unverified(self):
        """Test getting unverified user."""
        user = UserInDB(
            id="507f1f77bcf86cd799439011",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_password_value",
            subscription_plan="free",
            is_active=True,
            is_verified=False,  # Unverified
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_verified_user(user)

        assert exc_info.value.status_code == 403
        assert "verify your email" in str(exc_info.value.detail)


class TestGetCurrentAdminUser:
    """Test get_current_admin_user function."""

    @pytest.mark.asyncio
    async def test_get_current_admin_user_admin_plan(self):
        """Test getting admin user with admin plan."""
        user = UserInDB(
            id="507f1f77bcf86cd799439011",
            username="adminuser",
            email="admin@example.com",
            full_name="Admin User",
            hashed_password="hashed_password_value",
            subscription_plan="admin",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
        )

        result = await get_current_admin_user(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_get_current_admin_user_pro_plan(self):
        """Test getting admin user with pro plan."""
        user = UserInDB(
            id="507f1f77bcf86cd799439011",
            username="prouser",
            email="pro@example.com",
            full_name="Pro User",
            hashed_password="hashed_password_value",
            subscription_plan="pro",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
        )

        result = await get_current_admin_user(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_get_current_admin_user_free_plan(self):
        """Test getting admin user with free plan (should fail)."""
        user = UserInDB(
            id="507f1f77bcf86cd799439011",
            username="freeuser",
            email="free@example.com",
            full_name="Free User",
            hashed_password="hashed_password_value",
            subscription_plan="free",
            is_active=True,
            is_verified=True,
            created_at=datetime.now(timezone.utc),
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(user)

        assert exc_info.value.status_code == 403
        assert "Admin access required" in str(exc_info.value.detail)


class TestOptionalAuth:
    """Test OptionalAuth class."""

    def test_optional_auth_init(self):
        """Test OptionalAuth initialization."""
        auth = OptionalAuth()
        assert auth.security is not None

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_optional_auth_success(self, mock_verify_token):
        """Test optional auth with valid credentials."""
        user_id = "507f1f77bcf86cd799439011"
        mock_verify_token.return_value = {"sub": user_id}

        mock_db = MagicMock()
        mock_collection = AsyncMock()
        user_doc = {
            "_id": ObjectId(user_id),
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "hashed_password_value",
            "subscription_plan": "free",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.now(timezone.utc),
        }
        mock_collection.find_one.return_value = user_doc
        mock_db.users = mock_collection

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        auth = OptionalAuth()
        result = await auth(credentials, mock_db)

        assert isinstance(result, UserInDB)
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_optional_auth_no_credentials(self):
        """Test optional auth with no credentials."""
        mock_db = MagicMock()

        auth = OptionalAuth()
        result = await auth(None, mock_db)

        assert result is None

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_optional_auth_invalid_token(self, mock_verify_token):
        """Test optional auth with invalid token."""
        mock_verify_token.return_value = None
        mock_db = MagicMock()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        auth = OptionalAuth()
        result = await auth(credentials, mock_db)

        assert result is None

    @pytest.mark.asyncio
    @patch("app.middleware.auth.verify_token")
    async def test_optional_auth_exception(self, mock_verify_token):
        """Test optional auth with exception."""
        mock_verify_token.side_effect = Exception("Error")
        mock_db = MagicMock()

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="valid_token"
        )

        auth = OptionalAuth()
        result = await auth(credentials, mock_db)

        assert result is None
