#!/usr/bin/env python3
"""
Test environment access step by step to identify where WebSocket is failing.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.models.user import UserInDB
from app.services.environment_service import EnvironmentService


async def test_environment_access():
    """Test each step of environment access"""

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "devpocket")

    # Connect to database
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Get user
        user_id = ObjectId("6880cb54f9f0280f9e9f70c8")
        user_doc = await db.users.find_one({"_id": user_id})
        if not user_doc:
            print("❌ User not found")
            return

        user = UserInDB(**user_doc)
        print(f"✅ User found: {user.username}")

        # Initialize environment service
        env_service = EnvironmentService()
        env_service.set_database(db)

        # Test environment access
        environment_id = "68850093852e1ff1492d3d87"
        print(f"🔍 Testing environment access for: {environment_id}")

        environment = await env_service.get_environment(environment_id, str(user.id))
        if not environment:
            print("❌ Environment not found")
            return

        print(f"✅ Environment found: {environment.name}")
        print(f"   Status: {environment.status}")
        print(f"   Namespace: {environment.namespace}")
        print(f"   Pod name: {environment.pod_name}")

        # Check if environment is running
        if environment.status != "running":
            print(f"❌ Environment not running (status: {environment.status})")
            return

        print(f"✅ Environment is running")

        # Test get actual pod name
        print(f"🔍 Getting actual pod name...")
        actual_pod_name = await env_service.get_actual_pod_name(environment)
        if not actual_pod_name:
            print("❌ Pod not found in Kubernetes")
            return

        print(f"✅ Actual pod found: {actual_pod_name}")

        print(f"\n🎉 All environment access checks passed!")

    except Exception as e:
        print(f"❌ Error during environment access test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(test_environment_access())
