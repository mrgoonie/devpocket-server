import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.core.config import settings
from app.core.database import Database, get_database


# Test database configuration
TEST_DB_NAME = "devpocket_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_database():
    """Create test database connection."""
    # Use test database
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[TEST_DB_NAME]
    
    # Create database instance
    database = Database()
    database.client = client
    database.db = db
    
    # Create indexes
    await database.create_indexes()
    
    yield database
    
    # Cleanup - drop test database
    await client.drop_database(TEST_DB_NAME)
    client.close()


@pytest.fixture
async def client(test_database: Database) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with test database."""
    
    # Override database dependency
    async def get_test_database():
        return test_database.db
    
    app.dependency_overrides[get_database] = get_test_database
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    # Clean up dependency override
    app.dependency_overrides.clear()


@pytest.fixture
async def clean_database(test_database: Database):
    """Clean test database before each test."""
    # Drop all collections
    collections = await test_database.db.list_collection_names()
    for collection_name in collections:
        await test_database.db[collection_name].drop()
    
    # Recreate indexes
    await test_database.create_indexes()
    
    yield test_database
    

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def sample_login_data():
    """Sample login data for testing."""
    return {
        "username_or_email": "testuser",
        "password": "TestPassword123"
    }


@pytest.fixture
async def authenticated_user(client: AsyncClient, clean_database, sample_user_data):
    """Create and return authenticated user with token."""
    # Register user
    register_response = await client.post("/api/v1/auth/register", json=sample_user_data)
    assert register_response.status_code == 201
    
    # Login user
    login_data = {
        "username_or_email": sample_user_data["username"],
        "password": sample_user_data["password"]
    }
    login_response = await client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200
    
    token_data = login_response.json()
    
    return {
        "user": register_response.json(),
        "token": token_data["access_token"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"}
    }


@pytest.fixture
def sample_environment_data():
    """Sample environment data for testing."""
    return {
        "name": "test-env",
        "template": "python",
        "description": "Test environment"
    }