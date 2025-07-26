import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.database import Database, get_database
from app.main import app
from app.services.template_service import template_service

# Test database configuration
TEST_DB_NAME = "devpocket_test"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_database():
    """Create test database connection."""
    # Use test database
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[TEST_DB_NAME]

    # Create database instance
    database = Database()
    database.client = client
    database.database = db

    # Create indexes
    # Temporarily override the global db for index creation
    from app.core.database import create_indexes, db as global_db

    old_database = global_db.database
    global_db.database = db
    await create_indexes()
    global_db.database = old_database

    yield database

    # Cleanup - drop test database
    await client.drop_database(TEST_DB_NAME)
    client.close()


@pytest_asyncio.fixture
async def client(test_database: Database):
    """Create test client with test database."""

    # Seed default templates
    template_service.set_database(test_database.database)
    await template_service.initialize_default_templates()

    # Override database dependency
    async def get_test_database():
        return test_database.database

    app.dependency_overrides[get_database] = get_test_database

    # Also set the global database client for readiness checks
    from app.core.database import db as global_db

    global_db.client = test_database.client
    global_db.database = test_database.database

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # Clean up dependency override
    app.dependency_overrides.clear()

    # Clean up global database reference
    global_db.client = None
    global_db.database = None


@pytest_asyncio.fixture
async def clean_database(test_database: Database):
    """Clean test database before each test."""
    # Drop all collections
    collections = await test_database.database.list_collection_names()
    for collection_name in collections:
        await test_database.database[collection_name].drop()

    # Recreate indexes
    from app.core.database import create_indexes, db as global_db

    old_database = global_db.database
    global_db.database = test_database.database
    await create_indexes()
    global_db.database = old_database

    yield test_database.database


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_login_data():
    """Sample login data for testing."""
    return {"username_or_email": "testuser", "password": "TestPassword123"}


@pytest_asyncio.fixture
async def authenticated_user(client, clean_database, sample_user_data):
    """Create and return authenticated user with token."""
    # Register user
    register_response = await client.post(
        "/api/v1/auth/register", json=sample_user_data
    )
    assert register_response.status_code == 201

    # Login user
    login_data = {
        "username_or_email": sample_user_data["username"],
        "password": sample_user_data["password"],
    }
    login_response = await client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200

    token_data = login_response.json()

    return {
        "user": register_response.json(),
        "token": token_data["access_token"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"},
    }


@pytest.fixture
def sample_environment_data():
    """Sample environment data for testing."""
    return {"name": "test-env", "template": "python"}


@pytest_asyncio.fixture
async def admin_user(client, clean_database):
    """Create and return authenticated admin user with token."""
    # Create admin user data
    admin_data = {
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "AdminPassword123",
        "full_name": "Admin User",
    }

    # Register user
    register_response = await client.post("/api/v1/auth/register", json=admin_data)
    assert register_response.status_code == 201

    # Update user to admin in database - use clean_database directly
    from bson import ObjectId

    # Find user by username and update to admin AND verify
    result = await clean_database.users.update_one(
        {"username": "adminuser"},
        {"$set": {"subscription_plan": "admin", "is_verified": True}},
    )
    assert result.modified_count == 1, "Failed to update user to admin"

    # Login user AFTER updating to admin to get correct token
    login_data = {
        "username_or_email": admin_data["username"],
        "password": admin_data["password"],
    }
    login_response = await client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200

    token_data = login_response.json()

    # Verify the user is admin by getting current user info
    headers = {"Authorization": f"Bearer {token_data['access_token']}"}
    user_response = await client.get("/api/v1/auth/me", headers=headers)
    assert user_response.status_code == 200
    user_info = user_response.json()
    # Verify admin status
    # print(f"DEBUG: User info after login: {user_info}")
    # print(f"DEBUG: Subscription plan: {user_info.get('subscription_plan', 'NOT SET')}")
    assert (
        user_info["subscription_plan"] == "admin"
    ), f"User subscription plan is {user_info['subscription_plan']}, expected 'admin'"

    return {"user": user_info, "token": token_data["access_token"], "headers": headers}
