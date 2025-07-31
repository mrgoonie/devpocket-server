"""Tests for security module."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.security import (
    SecurityHeaders,
    create_access_token,
    create_refresh_token,
    generate_api_key,
    get_password_hash,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_and_verify_password(self):
        """Test password hashing and verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        # Hash should be different from original password
        assert hashed != password

        # Verification should work
        assert verify_password(password, hashed) is True

        # Wrong password should fail
        assert verify_password("wrong_password", hashed) is False

    def test_different_passwords_produce_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to salt
        assert hash1 != hash2

        # Both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenGeneration:
    """Test JWT token generation and verification."""

    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry."""
        data = {"sub": "test_user", "user_id": "123"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["user_id"] == "123"
        assert payload["type"] == "access_token"

    def test_create_access_token_custom_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)

        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"

        # Check expiry is approximately correct (within 1 minute)
        exp = datetime.fromtimestamp(payload["exp"], timezone.utc)
        expected_exp = datetime.now(timezone.utc) + expires_delta
        assert abs((exp - expected_exp).total_seconds()) < 60

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        data = {"sub": "test_user", "user_id": "123"}
        token = create_refresh_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token
        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["user_id"] == "123"
        assert payload["type"] == "refresh_token"

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        data = {"sub": "test_user", "user_id": "123"}
        token = create_access_token(data)

        payload = verify_token(token)
        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["user_id"] == "123"

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)
        assert payload is None

    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        data = {"sub": "test_user"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta)

        payload = verify_token(token)
        assert payload is None

    @patch("app.core.security.jwt.encode")
    def test_create_access_token_jwt_error(self, mock_encode):
        """Test access token creation with JWT error."""
        mock_encode.side_effect = Exception("JWT encoding failed")

        data = {"sub": "test_user"}
        with pytest.raises(HTTPException) as exc_info:
            create_access_token(data)

        assert exc_info.value.status_code == 500
        assert "Could not create access token" in str(exc_info.value.detail)

    @patch("app.core.security.jwt.encode")
    def test_create_refresh_token_jwt_error(self, mock_encode):
        """Test refresh token creation with JWT error."""
        mock_encode.side_effect = Exception("JWT encoding failed")

        data = {"sub": "test_user"}
        with pytest.raises(HTTPException) as exc_info:
            create_refresh_token(data)

        assert exc_info.value.status_code == 500
        assert "Could not create refresh token" in str(exc_info.value.detail)


class TestTokenVerification:
    """Test token verification edge cases."""

    @patch("app.core.security.jwt.decode")
    def test_verify_token_jwt_error(self, mock_decode):
        """Test token verification with JWT error."""
        from jose import JWTError

        mock_decode.side_effect = JWTError("Invalid token")

        payload = verify_token("invalid_token")
        assert payload is None

    @patch("app.core.security.jwt.decode")
    def test_verify_token_unexpected_error(self, mock_decode):
        """Test token verification with unexpected error."""
        mock_decode.side_effect = Exception("Unexpected error")

        payload = verify_token("some_token")
        assert payload is None

    def test_verify_token_no_expiry(self):
        """Test verifying token without expiry field."""
        # This is a bit tricky to test since our create functions always add exp
        # We'll mock the decode to return payload without exp
        with patch("app.core.security.jwt.decode") as mock_decode:
            mock_decode.return_value = {"sub": "test_user", "user_id": "123"}

            payload = verify_token("mock_token")
            assert payload is not None
            assert payload["sub"] == "test_user"


class TestApiKeyGeneration:
    """Test API key generation."""

    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()

        assert isinstance(api_key, str)
        assert api_key.startswith("dpk_")
        assert len(api_key) > 10  # Should be reasonably long

    def test_generate_unique_api_keys(self):
        """Test that generated API keys are unique."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        assert key1 != key2
        assert key1.startswith("dpk_")
        assert key2.startswith("dpk_")


class TestSecurityHeaders:
    """Test security headers."""

    def test_get_security_headers(self):
        """Test getting security headers."""
        headers = SecurityHeaders.get_security_headers()

        assert isinstance(headers, dict)

        # Check important security headers are present
        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
        ]

        for header in expected_headers:
            assert header in headers
            assert isinstance(headers[header], str)
            assert len(headers[header]) > 0

        # Check specific header values
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert "max-age=31536000" in headers["Strict-Transport-Security"]
        assert "default-src 'self'" in headers["Content-Security-Policy"]
