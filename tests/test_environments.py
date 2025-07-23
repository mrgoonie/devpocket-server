import pytest
from httpx import AsyncClient


class TestEnvironmentEndpoints:
    """Test environment management endpoints."""
    
    async def test_create_environment(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test creating a new environment."""
        response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == sample_environment_data["name"]
        assert data["template"] == sample_environment_data["template"]
        assert data["description"] == sample_environment_data["description"]
        assert data["status"] == "creating"
        assert data["user_id"] == authenticated_user["user"]["id"]
        assert "id" in data
        assert "created_at" in data
    
    async def test_create_environment_unauthorized(self, client: AsyncClient, sample_environment_data):
        """Test creating environment without authentication."""
        response = await client.post("/api/v1/environments/", json=sample_environment_data)
        
        assert response.status_code == 401
    
    async def test_create_environment_invalid_template(self, client: AsyncClient, authenticated_user):
        """Test creating environment with invalid template."""
        invalid_data = {
            "name": "test-env",
            "template": "invalid_template",
            "description": "Test environment"
        }
        
        response = await client.post(
            "/api/v1/environments/",
            json=invalid_data,
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_list_environments(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test listing user environments."""
        # Create an environment first
        await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        
        # List environments
        response = await client.get("/api/v1/environments/", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["name"] == sample_environment_data["name"]
    
    async def test_list_environments_unauthorized(self, client: AsyncClient):
        """Test listing environments without authentication."""
        response = await client.get("/api/v1/environments/")
        
        assert response.status_code == 401
    
    async def test_get_environment(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting a specific environment."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Get the environment
        response = await client.get(f"/api/v1/environments/{env_id}", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == env_id
        assert data["name"] == sample_environment_data["name"]
    
    async def test_get_environment_not_found(self, client: AsyncClient, authenticated_user):
        """Test getting non-existent environment."""
        fake_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format
        response = await client.get(f"/api/v1/environments/{fake_id}", headers=authenticated_user["headers"])
        
        assert response.status_code == 404
    
    async def test_get_environment_unauthorized(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting environment without proper authentication."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Try to get without token
        response = await client.get(f"/api/v1/environments/{env_id}")
        
        assert response.status_code == 401
    
    async def test_delete_environment(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test deleting an environment."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Delete the environment
        response = await client.delete(f"/api/v1/environments/{env_id}", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        
        # Verify it's deleted by trying to get it
        get_response = await client.get(f"/api/v1/environments/{env_id}", headers=authenticated_user["headers"])
        assert get_response.status_code == 404
    
    async def test_start_environment(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test starting an environment."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Start the environment
        response = await client.post(f"/api/v1/environments/{env_id}/start", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Environment started successfully"
    
    async def test_stop_environment(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test stopping an environment."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Stop the environment
        response = await client.post(f"/api/v1/environments/{env_id}/stop", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Environment stopped successfully"
    
    async def test_get_environment_metrics(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting environment metrics."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Get metrics
        response = await client.get(f"/api/v1/environments/{env_id}/metrics", headers=authenticated_user["headers"])
        
        assert response.status_code == 200
        data = response.json()
        
        # Should contain metrics structure
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "storage_usage" in data