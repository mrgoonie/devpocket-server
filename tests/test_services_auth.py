"""Tests for auth service."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi import HTTPException

from app.models.user import UserCreate, UserInDB, UserLogin
from app.services.auth_service import AuthService


class TestAuthService:
    """Test AuthService class."""

    def test_auth_service_init(self):
        """Test AuthService initialization."""
        service = AuthService()
        assert service.db is None

    def test_set_database(self):
        """Test setting database instance."""
        service = AuthService()
        mock_db = MagicMock()

        service.set_database(mock_db)
        assert service.db == mock_db

    def test_convert_objectid_to_string(self):
        """Test ObjectId to string conversion."""
        service = AuthService()

        # Test with ObjectId
        user_doc = {"_id": ObjectId("507f1f77bcf86cd799439011"), "username": "testuser"}

        result = service._convert_objectid_to_string(user_doc)
        assert isinstance(result["_id"], str)
        assert result["_id"] == "507f1f77bcf86cd799439011"

        # Test with None
        result = service._convert_objectid_to_string(None)
        assert result is None

        # Test without _id field
        user_doc_no_id = {"username": "testuser"}
        result = service._convert_objectid_to_string(user_doc_no_id)
        assert result == user_doc_no_id

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test successful user creation."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock no existing user
        mock_users_collection.find_one.return_value = None

        # Mock successful insert
        mock_users_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("507f1f77bcf86cd799439011")
        )

        # Mock finding the created user
        created_user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": False,
            "subscription_plan": "free",
            "created_at": datetime.now(timezone.utc),
        }
        mock_users_collection.find_one.side_effect = [None, created_user_doc]

        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            full_name="Test User",
        )

        with patch("app.services.auth_service.get_password_hash") as mock_hash:
            mock_hash.return_value = "hashed_password"

            result = await service.create_user(user_data)

            assert isinstance(result, UserInDB)
            assert result.username == "testuser"
            assert result.email == "test@example.com"
            mock_users_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock existing user with same email
        existing_user = {"email": "test@example.com", "username": "existing_user"}
        mock_users_collection.find_one.return_value = existing_user

        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            full_name="Test User",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert "email" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self):
        """Test user creation with duplicate username."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock existing user with same username
        existing_user = {"email": "other@example.com", "username": "testuser"}
        mock_users_collection.find_one.return_value = existing_user

        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
            full_name="Test User",
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_user(user_data)

        assert exc_info.value.status_code == 400
        assert "username" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock finding user
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": True,
            "failed_login_attempts": 0,
            "locked_until": None,
            "subscription_plan": "free",
            "created_at": datetime.now(timezone.utc),
        }
        mock_users_collection.find_one.return_value = user_doc

        login_data = UserLogin(username_or_email="testuser", password="TestPassword123")

        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = True

            result = await service.authenticate_user(login_data)

            assert isinstance(result, UserInDB)
            assert result.username == "testuser"
            mock_verify.assert_called_once_with("TestPassword123", "hashed_password")

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock finding user
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "hashed_password": "hashed_password",
            "failed_login_attempts": 0,
            "locked_until": None,
        }
        mock_users_collection.find_one.return_value = user_doc

        login_data = UserLogin(username_or_email="testuser", password="WrongPassword")

        with patch("app.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = False

            result = await service.authenticate_user(login_data)

            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock user not found
        mock_users_collection.find_one.return_value = None

        login_data = UserLogin(username_or_email="nonexistent", password="password")

        result = await service.authenticate_user(login_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_locked_account(self):
        """Test authentication with locked account."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock finding locked user
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "hashed_password": "hashed_password",
            "failed_login_attempts": 5,
            "locked_until": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        mock_users_collection.find_one.return_value = user_doc

        login_data = UserLogin(username_or_email="testuser", password="TestPassword123")

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate_user(login_data)

        assert exc_info.value.status_code == 423  # Locked

    @pytest.mark.asyncio
    async def test_handle_failed_login(self):
        """Test handling failed login attempts."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        user_id = "507f1f77bcf86cd799439011"

        await service._handle_failed_login(user_id)

        # Verify database update was called
        mock_users_collection.update_one.assert_called_once()
        call_args = mock_users_collection.update_one.call_args
        assert call_args[0][0] == {"_id": ObjectId(user_id)}

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self):
        """Test successful user retrieval by ID."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        user_id = "507f1f77bcf86cd799439011"
        user_doc = {
            "_id": ObjectId(user_id),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": True,
            "subscription_plan": "free",
            "created_at": datetime.now(timezone.utc),
        }
        mock_users_collection.find_one.return_value = user_doc

        result = await service.get_user_by_id(user_id)

        assert isinstance(result, UserInDB)
        assert result.username == "testuser"
        mock_users_collection.find_one.assert_called_once_with(
            {"_id": ObjectId(user_id)}
        )

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self):
        """Test user retrieval with non-existent ID."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        user_id = "507f1f77bcf86cd799439999"
        mock_users_collection.find_one.return_value = None

        result = await service.get_user_by_id(user_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_tokens(self):
        """Test JWT token creation."""
        service = AuthService()

        user = UserInDB(
            id="507f1f77bcf86cd799439011",
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            full_name="Test User",
            is_active=True,
            is_verified=True,
            subscription_plan="free",
            created_at=datetime.now(timezone.utc),
        )

        with patch(
            "app.services.auth_service.create_access_token"
        ) as mock_access, patch(
            "app.services.auth_service.create_refresh_token"
        ) as mock_refresh:
            mock_access.return_value = "access_token_123"
            mock_refresh.return_value = "refresh_token_456"

            result = await service.create_tokens(user)

            assert result.access_token == "access_token_123"
            assert result.refresh_token == "refresh_token_456"
            assert result.token_type == "bearer"

    @pytest.mark.asyncio
    async def test_refresh_tokens_success(self):
        """Test successful token refresh."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        refresh_token = "valid_refresh_token"

        # Mock token verification
        mock_payload = {"sub": "507f1f77bcf86cd799439011", "type": "refresh_token"}

        # Mock finding user
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "full_name": "Test User",
            "is_active": True,
            "is_verified": True,
            "subscription_plan": "free",
            "created_at": datetime.now(timezone.utc),
        }
        mock_users_collection.find_one.return_value = user_doc

        with patch("app.services.auth_service.verify_token") as mock_verify, patch(
            "app.services.auth_service.create_access_token"
        ) as mock_access, patch(
            "app.services.auth_service.create_refresh_token"
        ) as mock_refresh:
            mock_verify.return_value = mock_payload
            mock_access.return_value = "new_access_token"
            mock_refresh.return_value = "new_refresh_token"

            result = await service.refresh_tokens(refresh_token)

            assert result.access_token == "new_access_token"
            assert result.refresh_token == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_tokens_invalid_token(self):
        """Test token refresh with invalid token."""
        service = AuthService()
        service.set_database(MagicMock())

        with patch("app.services.auth_service.verify_token") as mock_verify:
            mock_verify.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await service.refresh_tokens("invalid_token")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_tokens_wrong_type(self):
        """Test token refresh with wrong token type."""
        service = AuthService()
        service.set_database(MagicMock())

        # Mock access token instead of refresh token
        mock_payload = {
            "sub": "507f1f77bcf86cd799439011",
            "type": "access_token",  # Wrong type
        }

        with patch("app.services.auth_service.verify_token") as mock_verify:
            mock_verify.return_value = mock_payload

            with pytest.raises(HTTPException) as exc_info:
                await service.refresh_tokens("access_token")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_generate_email_verification_token(self):
        """Test email verification token generation."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        user_id = "507f1f77bcf86cd799439011"

        with patch("app.services.auth_service.secrets.token_urlsafe") as mock_token:
            mock_token.return_value = "verification_token_123"

            result = await service.generate_email_verification_token(user_id)

            assert result == "verification_token_123"
            mock_users_collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_email_token_success(self):
        """Test successful email verification."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock finding user with valid token
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "email_verification_token": "valid_token",
            "email_verification_expires": datetime.now(timezone.utc)
            + timedelta(hours=1),
            "is_verified": False,
        }
        mock_users_collection.find_one.return_value = user_doc
        mock_users_collection.update_one.return_value = MagicMock(modified_count=1)

        result = await service.verify_email_token("valid_token")

        assert result is True
        # Verify user was updated to verified status
        mock_users_collection.update_one.assert_called()

    @pytest.mark.asyncio
    async def test_verify_email_token_invalid(self):
        """Test email verification with invalid token."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock user not found with token
        mock_users_collection.find_one.return_value = None

        result = await service.verify_email_token("invalid_token")
        assert result is False

    @pytest.mark.asyncio
    async def test_verify_email_token_expired(self):
        """Test email verification with expired token."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        # Mock finding user with expired token
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "email_verification_token": "expired_token",
            "email_verification_expires": datetime.now(timezone.utc)
            - timedelta(hours=1),  # Expired
            "is_verified": False,
        }
        mock_users_collection.find_one.return_value = user_doc

        result = await service.verify_email_token("expired_token")
        assert result is False

    @pytest.mark.asyncio
    async def test_google_login_success(self):
        """Test successful Google login."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        google_token = "valid_google_token"
        google_user_info = {
            "sub": "google_user_123",
            "email": "user@gmail.com",
            "name": "Google User",
            "picture": "https://example.com/avatar.jpg",
        }

        # Mock existing user
        user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "username": "googleuser",
            "email": "user@gmail.com",
            "google_id": "google_user_123",
            "hashed_password": "placeholder",
            "full_name": "Google User",
            "is_active": True,
            "is_verified": True,
            "subscription_plan": "free",
            "created_at": datetime.now(timezone.utc),
        }
        mock_users_collection.find_one.return_value = user_doc

        with patch(
            "app.services.auth_service.id_token.verify_oauth2_token"
        ) as mock_verify:
            mock_verify.return_value = google_user_info

            result = await service.google_login(google_token)

            assert isinstance(result, UserInDB)
            assert result.email == "user@gmail.com"

    @pytest.mark.asyncio
    async def test_google_login_invalid_token(self):
        """Test Google login with invalid token."""
        service = AuthService()
        service.set_database(MagicMock())

        with patch(
            "app.services.auth_service.id_token.verify_oauth2_token"
        ) as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")

            with pytest.raises(HTTPException) as exc_info:
                await service.google_login("invalid_token")

            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_google_login_new_user_creation(self):
        """Test Google login creating new user."""
        service = AuthService()
        mock_db = MagicMock()
        mock_users_collection = AsyncMock()
        mock_db.users = mock_users_collection
        service.set_database(mock_db)

        google_token = "valid_google_token"
        google_user_info = {
            "sub": "new_google_user_123",
            "email": "newuser@gmail.com",
            "name": "New Google User",
            "picture": "https://example.com/avatar.jpg",
        }

        # Mock user not found initially, then return created user
        created_user_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439012"),
            "username": "newgoogleuser",
            "email": "newuser@gmail.com",
            "google_id": "new_google_user_123",
            "hashed_password": "placeholder",
            "full_name": "New Google User",
            "is_active": True,
            "is_verified": True,
            "subscription_plan": "free",
            "created_at": datetime.now(timezone.utc),
        }

        mock_users_collection.find_one.side_effect = [None, created_user_doc]
        mock_users_collection.insert_one.return_value = MagicMock(
            inserted_id=ObjectId("507f1f77bcf86cd799439012")
        )

        with patch(
            "app.services.auth_service.id_token.verify_oauth2_token"
        ) as mock_verify:
            mock_verify.return_value = google_user_info

            result = await service.google_login(google_token)

            assert isinstance(result, UserInDB)
            assert result.email == "newuser@gmail.com"
            assert result.google_id == "new_google_user_123"
            mock_users_collection.insert_one.assert_called_once()


# Create auth service instance for testing
auth_service = AuthService()
