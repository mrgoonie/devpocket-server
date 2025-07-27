#!/usr/bin/env python3
"""
Fix environment data in database - update namespace and pod_name fields.
"""

import asyncio
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


async def fix_environment_data():
    """Fix environment data in database"""

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "devpocket")

    # Connect to database
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Get the environment
        env_id = ObjectId("68850093852e1ff1492d3d87")
        env = await db.environments.find_one({"_id": env_id})

        if env:
            print(f"Found environment: {env.get('name')}")
            print(f"Current namespace: {env.get('namespace')}")
            print(f"Current pod_name: {env.get('pod_name')}")

            # Check if we need to update
            if not env.get("namespace") or not env.get("pod_name"):
                print("\n⚠️ Missing namespace or pod_name, updating...")

                update_data = {}
                if not env.get("namespace"):
                    update_data["namespace"] = "user-6880cb54f9f0280f9e9f70c8"
                if not env.get("pod_name"):
                    update_data["pod_name"] = "goon-ea07939a"

                result = await db.environments.update_one(
                    {"_id": env_id}, {"$set": update_data}
                )

                if result.modified_count > 0:
                    print("✅ Environment data updated successfully")

                    # Verify update
                    updated_env = await db.environments.find_one({"_id": env_id})
                    print(f"\nUpdated namespace: {updated_env.get('namespace')}")
                    print(f"Updated pod_name: {updated_env.get('pod_name')}")
                else:
                    print("❌ Failed to update environment data")
            else:
                print("\n✅ Environment data is already complete")
        else:
            print("❌ Environment not found")

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(fix_environment_data())
