#!/usr/bin/env python3
"""
Check environments directly from database to bypass API redirect issues.
"""

import asyncio
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


async def check_environments():
    """Check existing environments from database"""

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "devpocket")

    # Connect to database
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Get all environments for the goon user
        user_id = ObjectId("6880cb54f9f0280f9e9f70c8")

        environments = await db.environments.find({"user_id": user_id}).to_list(
            length=None
        )

        print(f"Found {len(environments)} environments for user goon:")

        for env in environments:
            print(f"\n  Environment:")
            print(f"    ID: {env.get('_id')}")
            print(f"    Name: {env.get('name')}")
            print(f"    Status: {env.get('status')}")
            print(f"    Namespace: {env.get('namespace')}")
            print(f"    Pod name: {env.get('pod_name')}")
            print(f"    Created: {env.get('created_at')}")

        # Return the most recent running environment if any
        running_envs = [env for env in environments if env.get("status") == "running"]
        if running_envs:
            latest_env = sorted(
                running_envs, key=lambda x: x.get("created_at", ""), reverse=True
            )[0]
            print(f"\nMost recent running environment: {latest_env.get('_id')}")
            return str(latest_env.get("_id"))
        else:
            print("\nNo running environments found")
            return None

    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(check_environments())
