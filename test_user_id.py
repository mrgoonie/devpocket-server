#!/usr/bin/env python3
"""
Test user ID representation.
"""

import asyncio
import os

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

from app.models.user import UserInDB


async def test_user_id():
    """Test how user ID is represented"""

    # Get MongoDB URL from environment
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    database_name = os.getenv("DATABASE_NAME", "devpocket")

    # Connect to database
    client = AsyncIOMotorClient(mongodb_url)
    db = client[database_name]

    try:
        # Get user from database
        user_id = ObjectId("6880cb54f9f0280f9e9f70c8")
        user_doc = await db.users.find_one({"_id": user_id})

        if user_doc:
            user = UserInDB(**user_doc)
            print(f"User found: {user.username}")
            print(f"user.id: '{user.id}' (type: {type(user.id)})")
            print(f"str(user.id): '{str(user.id)}' (type: {type(str(user.id))})")

            # Test environment query
            env_id = "68850093852e1ff1492d3d87"

            # Try query with user.id directly
            query1 = {"_id": ObjectId(env_id), "user_id": user.id}
            env1 = await db.environments.find_one(query1)
            print(f"Query with user.id: {env1 is not None}")

            # Try query with str(user.id)
            query2 = {"_id": ObjectId(env_id), "user_id": str(user.id)}
            env2 = await db.environments.find_one(query2)
            print(f"Query with str(user.id): {env2 is not None}")

            # Check what's actually in the environment document
            env_doc = await db.environments.find_one({"_id": ObjectId(env_id)})
            if env_doc:
                print(
                    f"Environment user_id in DB: '{env_doc.get('user_id')}' (type: {type(env_doc.get('user_id'))})"
                )

        else:
            print("User not found")

    finally:
        client.close()


if __name__ == "__main__":
    import sys

    sys.path.insert(0, "app")
    asyncio.run(test_user_id())
