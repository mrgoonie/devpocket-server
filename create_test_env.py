#!/usr/bin/env python3
"""
Create a test environment directly using the service layer to bypass API issues.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from datetime import datetime, timezone

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.models.environment import EnvironmentCreate, ResourceLimits
from app.models.user import UserInDB
from app.services.environment_service import EnvironmentService


async def create_test_environment():
    """Create a test environment using service layer"""

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "devpocket")

    # Connect to database
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Initialize environment service
        env_service = EnvironmentService()
        env_service.set_database(db)

        # Get user from database
        user_id = ObjectId("6880cb54f9f0280f9e9f70c8")
        user_doc = await db.users.find_one({"_id": user_id})
        if not user_doc:
            print("❌ User not found in database")
            return None

        user = UserInDB(**user_doc)

        # Create environment data
        env_data = EnvironmentCreate(
            name="test-ws-terminal",
            template="ubuntu",
            resources=ResourceLimits(cpu="500m", memory="1Gi", storage="5Gi"),
            environment_variables={"TEST_VAR": "test_value"},
        )

        print("🚀 Creating test environment...")
        print(f"   Name: {env_data.name}")
        print(f"   Template: {env_data.template}")
        print(f"   User: {user.username} ({user.id})")

        # Create environment
        environment = await env_service.create_environment(user, env_data)

        print(f"✅ Environment created successfully!")
        print(f"   ID: {environment.id}")
        print(f"   Status: {environment.status}")
        print(f"   Namespace: {environment.namespace}")
        print(f"   Pod name: {environment.pod_name}")

        return str(environment.id)

    except Exception as e:
        print(f"❌ Failed to create environment: {e}")
        import traceback

        traceback.print_exc()
        return None

    finally:
        client.close()


if __name__ == "__main__":
    env_id = asyncio.run(create_test_environment())
    if env_id:
        print(f"\n🎯 Use this environment ID for WebSocket testing: {env_id}")
    else:
        print("\n❌ Failed to create test environment")
