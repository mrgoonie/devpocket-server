#!/usr/bin/env python3
"""
Check all environments in database regardless of user.
"""

import asyncio
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


async def check_all_environments():
    """Check all environments from database"""

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "devpocket")

    # Connect to database
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Get all environments
        environments = await db.environments.find({}).to_list(length=None)

        print(f"Found {len(environments)} total environments:")

        for env in environments:
            print(f"\n  Environment:")
            print(f"    ID: {env.get('_id')}")
            print(f"    Name: {env.get('name')}")
            print(f"    Status: {env.get('status')}")
            print(f"    User ID: {env.get('user_id')}")
            print(f"    Namespace: {env.get('namespace')}")
            print(f"    Pod name: {env.get('pod_name')}")
            print(f"    Created: {env.get('created_at')}")

        # Check for specific user
        user_id = ObjectId("6880cb54f9f0280f9e9f70c8")
        user_envs = await db.environments.find({"user_id": user_id}).to_list(
            length=None
        )

        print(f"\nEnvironments for user 6880cb54f9f0280f9e9f70c8: {len(user_envs)}")

        # Check user-id as string too
        user_envs_str = await db.environments.find(
            {"user_id": "6880cb54f9f0280f9e9f70c8"}
        ).to_list(length=None)

        print(
            f"Environments for user '6880cb54f9f0280f9e9f70c8' (string): {len(user_envs_str)}"
        )

        # Check active environments for this user
        active_envs = await db.environments.find(
            {"user_id": user_id, "status": {"$in": ["creating", "running"]}}
        ).to_list(length=None)

        print(f"Active environments for user (ObjectId): {len(active_envs)}")

        active_envs_str = await db.environments.find(
            {
                "user_id": "6880cb54f9f0280f9e9f70c8",
                "status": {"$in": ["creating", "running"]},
            }
        ).to_list(length=None)

        print(f"Active environments for user (string): {len(active_envs_str)}")

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(check_all_environments())
