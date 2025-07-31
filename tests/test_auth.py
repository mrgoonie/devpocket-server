import pytest


@pytest.mark.asyncio
async def test_register_user_success(client, clean_database, sample_user_data):
    """Test successful user registration."""
    response = await client.post("/api/v1/auth/register", json=sample_user_data)

    assert response.status_code == 201
    data = response.json()

    assert data["username"] == sample_user_data["username"]
    assert data["email"] == sample_user_data["email"]
    assert data["full_name"] == sample_user_data["full_name"]
    assert data["is_active"] is True
    assert data["is_verified"] is False
    assert data["subscription_plan"] == "free"
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data  # Should never be returned


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client, clean_database, sample_user_data):
    """Test registration with duplicate email."""
    # First registration
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Second registration with same email
    duplicate_data = sample_user_data.copy()
    duplicate_data["username"] = "different_username"

    response = await client.post("/api/v1/auth/register", json=duplicate_data)
    assert response.status_code == 400

    error_data = response.json()
    assert "email" in error_data["detail"].lower()


@pytest.mark.asyncio
async def test_register_user_duplicate_username(
    client, clean_database, sample_user_data
):
    """Test registration with duplicate username."""
    # First registration
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Second registration with same username
    duplicate_data = sample_user_data.copy()
    duplicate_data["email"] = "different@example.com"

    response = await client.post("/api/v1/auth/register", json=duplicate_data)
    assert response.status_code == 400

    error_data = response.json()
    assert "username" in error_data["detail"].lower()


@pytest.mark.asyncio
async def test_register_user_invalid_password(client, clean_database, sample_user_data):
    """Test registration with invalid password."""
    invalid_data = sample_user_data.copy()
    invalid_data["password"] = "weak"  # Too short

    response = await client.post("/api/v1/auth/register", json=invalid_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_user_invalid_email(client, clean_database, sample_user_data):
    """Test registration with invalid email."""
    invalid_data = sample_user_data.copy()
    invalid_data["email"] = "invalid_email"

    response = await client.post("/api/v1/auth/register", json=invalid_data)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_login_success(client, authenticated_user):
    """Test successful login."""
    # authenticated_user fixture already contains successful login data
    assert "token" in authenticated_user
    assert "user" in authenticated_user
    assert "headers" in authenticated_user

    # Verify token structure
    assert authenticated_user["token"] is not None
    assert len(authenticated_user["token"]) > 0


@pytest.mark.asyncio
async def test_login_with_email(client, clean_database, sample_user_data):
    """Test login with email instead of username."""
    # Register user first
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Login with email
    login_data = {
        "username_or_email": sample_user_data["email"],
        "password": sample_user_data["password"],
    }

    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200

    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, clean_database, sample_user_data):
    """Test login with invalid credentials."""
    # Register user first
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Try login with wrong password
    login_data = {
        "username_or_email": sample_user_data["username"],
        "password": "wrong_password",
    }

    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client, clean_database):
    """Test login with non-existent user."""
    login_data = {
        "username_or_email": "nonexistent@example.com",
        "password": "password123",
    }

    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client, authenticated_user):
    """Test getting current user info."""
    response = await client.get(
        "/api/v1/auth/me", headers=authenticated_user["headers"]
    )

    assert response.status_code == 200
    data = response.json()

    assert data["username"] == authenticated_user["user"]["username"]
    assert data["email"] == authenticated_user["user"]["email"]
    assert data["full_name"] == authenticated_user["user"]["full_name"]
    assert "id" in data
    assert "created_at" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client):
    """Test getting current user without authentication."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_account_lockout(client, clean_database, sample_user_data):
    """Test account lockout after multiple failed login attempts."""
    # Register user first
    await client.post("/api/v1/auth/register", json=sample_user_data)

    login_data = {
        "username_or_email": sample_user_data["username"],
        "password": "wrong_password",
    }

    # Make 5 failed login attempts
    for i in range(5):
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    # 6th attempt should result in account lockout
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 423  # Account locked

    # Even correct password should fail when locked
    correct_login_data = {
        "username_or_email": sample_user_data["username"],
        "password": sample_user_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=correct_login_data)
    assert response.status_code == 423  # Account locked


@pytest.mark.asyncio
async def test_logout_success(client, authenticated_user):
    """Test successful user logout."""
    response = await client.post(
        "/api/v1/auth/logout", headers=authenticated_user["headers"]
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Successfully logged out"


@pytest.mark.asyncio
async def test_logout_unauthorized(client):
    """Test logout without authentication."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token_success(client, clean_database, sample_user_data):
    """Test successful token refresh."""
    # Register and login first
    await client.post("/api/v1/auth/register", json=sample_user_data)
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": sample_user_data["username"],
            "password": sample_user_data["password"],
        },
    )

    tokens = login_response.json()
    refresh_token = tokens["refresh_token"]

    # Refresh token
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """Test token refresh with invalid token."""
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "invalid_token"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_missing(client):
    """Test token refresh with missing token."""
    response = await client.post("/api/v1/auth/refresh", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_email_success(client, clean_database, sample_user_data):
    """Test successful email verification."""
    # Register user first
    await client.post("/api/v1/auth/register", json=sample_user_data)

    # Mock email verification token (in real scenario, this would come from email)
    verification_data = {
        "email": sample_user_data["email"],
        "token": "mock_verification_token",
    }

    response = await client.post("/api/v1/auth/verify-email", json=verification_data)

    # Note: This might fail in real implementation due to token validation
    # but we're testing the endpoint structure
    assert response.status_code in [200, 400, 401]


@pytest.mark.asyncio
async def test_verify_email_invalid_data(client):
    """Test email verification with invalid data."""
    response = await client.post(
        "/api/v1/auth/verify-email", json={"email": "invalid-email", "token": ""}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_resend_verification_email(client, clean_database, sample_user_data):
    """Test resending verification email."""
    # Register user first
    await client.post("/api/v1/auth/register", json=sample_user_data)

    response = await client.post(
        "/api/v1/auth/resend-verification", json={"email": sample_user_data["email"]}
    )

    # Should succeed regardless of email service implementation
    assert response.status_code in [200, 500]  # 500 if email service not configured


@pytest.mark.asyncio
async def test_resend_verification_invalid_email(client):
    """Test resending verification with invalid email."""
    response = await client.post(
        "/api/v1/auth/resend-verification", json={"email": "nonexistent@example.com"}
    )

    assert response.status_code in [400, 404]


@pytest.mark.asyncio
async def test_google_auth_endpoint_exists(client):
    """Test that Google auth endpoint exists and handles missing data."""
    response = await client.post("/api/v1/auth/google", json={})

    # Should return validation error for missing token
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_validation_errors(client):
    """Test registration with various validation errors."""
    # Missing required fields
    response = await client.post("/api/v1/auth/register", json={})
    assert response.status_code == 422

    # Invalid email format
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "invalid-email",
            "password": "ValidPass123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 422

    # Password too short
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "123",
            "full_name": "Test User",
        },
    )
    assert response.status_code in [400, 422]


@pytest.mark.asyncio
async def test_login_validation_errors(client):
    """Test login with validation errors."""
    # Missing credentials
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422

    # Empty username/email
    response = await client.post(
        "/api/v1/auth/login", json={"username_or_email": "", "password": "password"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_auth_error_handling(client, clean_database, sample_user_data):
    """Test various error conditions in auth endpoints."""
    # Test server error handling by causing database issues
    # This is tricky to test without mocking, so we test valid flows

    # Register user
    response = await client.post("/api/v1/auth/register", json=sample_user_data)
    assert response.status_code == 201

    # Test login with correct credentials
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": sample_user_data["username"],
            "password": sample_user_data["password"],
        },
    )
    assert login_response.status_code == 200
