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
    assert data["is_active"] == True
    assert data["is_verified"] == False
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
async def test_register_user_duplicate_username(client, clean_database, sample_user_data):
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
        "password": sample_user_data["password"]
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
        "password": "wrong_password"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client, clean_database):
    """Test login with non-existent user."""
    login_data = {
        "username_or_email": "nonexistent@example.com",
        "password": "password123"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client, authenticated_user):
    """Test getting current user info."""
    response = await client.get("/api/v1/auth/me", headers=authenticated_user["headers"])
    
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
        "password": "wrong_password"
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
        "password": sample_user_data["password"]
    }
    response = await client.post("/api/v1/auth/login", json=correct_login_data)
    assert response.status_code == 423  # Account locked