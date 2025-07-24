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
        assert "environment_id" in data
        assert "metrics" in data
    
    async def test_restart_environment(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test restarting an environment."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Wait a bit to simulate environment being ready
        import asyncio
        await asyncio.sleep(0.1)
        
        # Update environment status to running (simulating it's ready)
        from app.core.database import get_database
        db = await anext(get_database())
        await db.environments.update_one(
            {"_id": env_id},
            {"$set": {"status": "running"}}
        )
        
        # Restart the environment
        response = await client.post(
            f"/api/v1/environments/{env_id}/restart",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Environment restart initiated successfully"
    
    async def test_restart_environment_invalid_state(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test restarting an environment in invalid state."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Try to restart while still creating
        response = await client.post(
            f"/api/v1/environments/{env_id}/restart",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 400
        assert "cannot be restarted" in response.json()["detail"]
    
    async def test_restart_environment_not_found(self, client: AsyncClient, authenticated_user):
        """Test restarting non-existent environment."""
        fake_id = "507f1f77bcf86cd799439011"
        response = await client.post(
            f"/api/v1/environments/{fake_id}/restart",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 404
    
    async def test_restart_environment_unauthorized(self, client: AsyncClient):
        """Test restarting environment without authentication."""
        fake_id = "507f1f77bcf86cd799439011"
        response = await client.post(f"/api/v1/environments/{fake_id}/restart")
        
        assert response.status_code == 401
    
    async def test_get_environment_logs(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting environment logs."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Get logs
        response = await client.get(
            f"/api/v1/environments/{env_id}/logs",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "environment_id" in data
        assert "environment_name" in data
        assert "logs" in data
        assert "total_lines" in data
        assert "has_more" in data
        
        # Check log structure
        assert isinstance(data["logs"], list)
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            assert "timestamp" in log
            assert "level" in log
            assert "message" in log
            assert "source" in log
    
    async def test_get_environment_logs_with_lines_param(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting environment logs with custom line count."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Get logs with specific line count
        response = await client.get(
            f"/api/v1/environments/{env_id}/logs",
            params={"lines": 50},
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["logs"]) <= 50
    
    async def test_get_environment_logs_with_since_param(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting environment logs with timestamp filter."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Get logs since specific timestamp
        from datetime import datetime, timezone
        since_time = datetime.now(timezone.utc).isoformat()
        
        response = await client.get(
            f"/api/v1/environments/{env_id}/logs",
            params={"since": since_time},
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All logs should be after the since timestamp
        for log in data["logs"]:
            log_time = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
            since_dt = datetime.fromisoformat(since_time.replace('Z', '+00:00'))
            assert log_time >= since_dt
    
    async def test_get_environment_logs_invalid_timestamp(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting environment logs with invalid timestamp."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Get logs with invalid timestamp
        response = await client.get(
            f"/api/v1/environments/{env_id}/logs",
            params={"since": "invalid-timestamp"},
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 400
        assert "Invalid timestamp format" in response.json()["detail"]
    
    async def test_get_environment_logs_invalid_lines(self, client: AsyncClient, authenticated_user, sample_environment_data):
        """Test getting environment logs with invalid line count."""
        # Create an environment first
        create_response = await client.post(
            "/api/v1/environments/",
            json=sample_environment_data,
            headers=authenticated_user["headers"]
        )
        env_id = create_response.json()["id"]
        
        # Test with too many lines
        response = await client.get(
            f"/api/v1/environments/{env_id}/logs",
            params={"lines": 2000},
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 422  # Validation error
        
        # Test with zero lines
        response = await client.get(
            f"/api/v1/environments/{env_id}/logs",
            params={"lines": 0},
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 422  # Validation error
    
    async def test_get_environment_logs_not_found(self, client: AsyncClient, authenticated_user):
        """Test getting logs for non-existent environment."""
        fake_id = "507f1f77bcf86cd799439011"
        response = await client.get(
            f"/api/v1/environments/{fake_id}/logs",
            headers=authenticated_user["headers"]
        )
        
        assert response.status_code == 404
    
    async def test_get_environment_logs_unauthorized(self, client: AsyncClient):
        """Test getting logs without authentication."""
        fake_id = "507f1f77bcf86cd799439011"
        response = await client.get(f"/api/v1/environments/{fake_id}/logs")
        
        assert response.status_code == 401