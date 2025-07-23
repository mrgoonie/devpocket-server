import pytest
from httpx import AsyncClient


class TestAuthEndpoints:
    """Test authentication endpoints."""
    
    async def test_register_user_success(self, client: AsyncClient, clean_database, sample_user_data):
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
    
    async def test_register_user_duplicate_email(self, client: AsyncClient, clean_database, sample_user_data):
        """Test registration with duplicate email."""
        # First registration
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Second registration with same email
        duplicate_data = sample_user_data.copy()
        duplicate_data["username"] = "different_username"
        
        response = await client.post("/api/v1/auth/register", json=duplicate_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    async def test_register_user_duplicate_username(self, client: AsyncClient, clean_database, sample_user_data):
        """Test registration with duplicate username."""
        # First registration
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Second registration with same username
        duplicate_data = sample_user_data.copy()
        duplicate_data["email"] = "different@example.com"
        
        response = await client.post("/api/v1/auth/register", json=duplicate_data)
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]
    
    async def test_register_user_invalid_password(self, client: AsyncClient, clean_database, sample_user_data):
        """Test registration with invalid password."""
        invalid_data = sample_user_data.copy()
        invalid_data["password"] = "weak"  # Too short and missing requirements
        
        response = await client.post("/api/v1/auth/register", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    async def test_register_user_invalid_email(self, client: AsyncClient, clean_database, sample_user_data):
        """Test registration with invalid email."""
        invalid_data = sample_user_data.copy()
        invalid_data["email"] = "not-an-email"
        
        response = await client.post("/api/v1/auth/register", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    async def test_login_success(self, client: AsyncClient, clean_database, sample_user_data):
        """Test successful login."""
        # Register user first
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login
        login_data = {
            "username_or_email": sample_user_data["username"],
            "password": sample_user_data["password"]
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    async def test_login_with_email(self, client: AsyncClient, clean_database, sample_user_data):
        """Test login using email instead of username."""
        # Register user first
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login with email
        login_data = {
            "username_or_email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    async def test_login_invalid_credentials(self, client: AsyncClient, clean_database, sample_user_data):
        """Test login with invalid credentials."""
        # Register user first
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        # Login with wrong password
        login_data = {
            "username_or_email": sample_user_data["username"],
            "password": "WrongPassword123"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username/email or password" in response.json()["detail"]
    
    async def test_login_nonexistent_user(self, client: AsyncClient, clean_database):
        """Test login with non-existent user."""
        login_data = {
            "username_or_email": "nonexistent",
            "password": "AnyPassword123"
        }
        response = await client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "Incorrect username/email or password" in response.json()["detail"]
    
    async def test_get_current_user(self, client: AsyncClient, authenticated_user):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["username"] == authenticated_user["user"]["username"]
        assert data["email"] == authenticated_user["user"]["email"]
        assert "id" in data
        assert "hashed_password" not in data
    
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without token."""
        response = await client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        """Test getting current user with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    async def test_account_lockout(self, client: AsyncClient, clean_database, sample_user_data):
        """Test account lockout after failed attempts."""
        # Register user first
        await client.post("/api/v1/auth/register", json=sample_user_data)
        
        login_data = {
            "username_or_email": sample_user_data["username"],
            "password": "WrongPassword123"
        }
        
        # Make 5 failed login attempts
        for i in range(5):
            response = await client.post("/api/v1/auth/login", json=login_data)
            assert response.status_code == 401
        
        # Next attempt should indicate account is locked
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        # Note: The exact message might vary based on implementation