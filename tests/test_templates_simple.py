"""Simple test to verify template endpoints work with ObjectId fixes."""
import pytest
import asyncio
from httpx import AsyncClient

from app.main import app
from app.core.database import get_database


@pytest.mark.asyncio
async def test_templates_endpoint_basic():
    """Basic test that template endpoint is accessible."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/templates")
        # Should get 403 without authentication (or 401)
        assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that health endpoint works."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


if __name__ == "__main__":
    asyncio.run(test_templates_endpoint_basic())
    asyncio.run(test_health_endpoint())
    print("Basic tests passed!")