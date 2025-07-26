import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_health_check(self, client: AsyncClient):
        """Test basic health check."""
        response = await client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "DevPocket API"
        assert "version" in data
        assert "timestamp" in data
    
    async def test_readiness_check(self, client: AsyncClient):
        """Test readiness check."""
        response = await client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["database"] == "healthy"
    
    async def test_liveness_check(self, client: AsyncClient):
        """Test liveness check."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"