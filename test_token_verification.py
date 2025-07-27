#!/usr/bin/env python3
"""
Test JWT token verification manually.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from jose import jwt
from motor.motor_asyncio import AsyncIOMotorClient


async def test_token():
    """Test token verification"""

    # Create token
    secret_key = os.getenv("SECRET_KEY", "9XX36cij9crf1VJPFUjphfZlk8vfuOBok5pxkHa-YsU")
    payload = {
        "sub": "6880cb54f9f0280f9e9f70c8",
        "username": "goon",
        "email": "goon.nguyen@gmail.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "type": "access_token",
    }
    access_token = jwt.encode(payload, secret_key, algorithm="HS256")

    print(f"Generated token: {access_token}")

    # Verify token
    try:
        decoded_payload = jwt.decode(access_token, secret_key, algorithms=["HS256"])
        print(f"Token decoded successfully: {decoded_payload}")

        user_id = decoded_payload.get("sub")
        print(f"User ID from token: {user_id}")

        # Check user in database
        mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        database_name = os.getenv("DATABASE_NAME", "devpocket")

        client = AsyncIOMotorClient(mongodb_url)
        db = client[database_name]

        try:
            user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
            if user_doc:
                print(
                    f"User found in database: {user_doc.get('username')} (active: {user_doc.get('is_active')})"
                )
            else:
                print("User not found in database")

        finally:
            client.close()

    except Exception as e:
        print(f"Token verification failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_token())
