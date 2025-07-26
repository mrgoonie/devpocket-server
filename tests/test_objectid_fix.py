import pytest
from bson import ObjectId
from httpx import AsyncClient


class TestObjectIdFix:
    """Test that ObjectId validation issues are resolved."""

    async def test_user_creation_with_objectid_validation(
        self, client: AsyncClient, clean_database, sample_user_data
    ):
        """Test that user creation properly handles ObjectId conversion."""
        response = await client.post("/api/v1/auth/register", json=sample_user_data)

        assert response.status_code == 201
        data = response.json()

        # Verify the ID is returned as a string (not ObjectId)
        assert isinstance(data["id"], str)
        assert ObjectId.is_valid(
            data["id"]
        )  # Should be valid ObjectId format but as string

    async def test_login_with_existing_user_objectid_fix(
        self, client: AsyncClient, clean_database, sample_user_data
    ):
        """Test that login works with ObjectId conversion fix."""
        # Register user first
        register_response = await client.post(
            "/api/v1/auth/register", json=sample_user_data
        )
        assert register_response.status_code == 201

        # Now login - this should work without ObjectId validation errors
        login_data = {
            "username_or_email": sample_user_data["username"],
            "password": sample_user_data["password"],
        }

        login_response = await client.post("/api/v1/auth/login", json=login_data)

        assert login_response.status_code == 200
        token_data = login_response.json()

        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"

    async def test_get_current_user_objectid_conversion(
        self, client: AsyncClient, authenticated_user
    ):
        """Test that getting current user works with ObjectId conversion."""
        response = await client.get(
            "/api/v1/auth/me", headers=authenticated_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()

        # Verify the ID is returned as a string
        assert isinstance(data["id"], str)
        assert ObjectId.is_valid(data["id"])

        # Verify other fields are correct
        assert data["username"] == authenticated_user["user"]["username"]
        assert data["email"] == authenticated_user["user"]["email"]
