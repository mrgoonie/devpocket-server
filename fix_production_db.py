#!/usr/bin/env python3
"""
Fix production database environment record directly.
"""

import asyncio
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


async def fix_production_db():
    """Fix production environment data directly in database"""

    # Use production MongoDB URL if available
    mongodb_url = os.getenv(
        "MONGODB_URL", "mongodb://devpocket:devpocket@localhost:27017"
    )
    database_name = os.getenv("DATABASE_NAME", "devpocket")

    print(
        f"🔌 Connecting to MongoDB: {mongodb_url.replace('devpocket:devpocket@', '***:***@')}"
    )

    # Connect to database
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Get the environment
        env_id = ObjectId("68850093852e1ff1492d3d87")
        env = await db.environments.find_one({"_id": env_id})

        if env:
            print(f"✅ Found environment: {env.get('name')}")
            print(f"   Current namespace: {env.get('namespace')}")
            print(f"   Current pod_name: {env.get('pod_name')}")

            # Update with correct data
            update_data = {
                "namespace": "user-6880cb54f9f0280f9e9f70c8",
                "pod_name": "goon-ea07939a-588cf5dd4f-pnftp",
            }

            print(f"\n🔧 Updating environment with:")
            print(f"   Namespace: {update_data['namespace']}")
            print(f"   Pod name: {update_data['pod_name']}")

            result = await db.environments.update_one(
                {"_id": env_id}, {"$set": update_data}
            )

            if result.modified_count > 0:
                print("✅ Environment data updated successfully")

                # Verify update
                updated_env = await db.environments.find_one({"_id": env_id})
                print(f"\n📋 Verified update:")
                print(f"   Namespace: {updated_env.get('namespace')}")
                print(f"   Pod name: {updated_env.get('pod_name')}")
                return True
            else:
                print("❌ Failed to update environment data")
                return False
        else:
            print("❌ Environment not found")
            return False

    finally:
        client.close()


if __name__ == "__main__":
    success = asyncio.run(fix_production_db())
    if success:
        print("\n🎉 Environment data fixed! WebSocket connection should work now.")
    else:
        print("\n❌ Failed to fix environment data.")
