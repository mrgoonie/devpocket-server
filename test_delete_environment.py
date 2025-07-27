#!/usr/bin/env python3
"""
Delete existing environment to make room for new test.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt


async def delete_environment():
    """Delete existing environment via API"""

    # Create JWT token
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

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # First list environments
    async with httpx.AsyncClient() as client:
        print("📋 Listing environments...")
        response = await client.get(
            "https://devpocket-api.goon.vn/api/v1/environments/",
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            environments = response.json()
            print(f"Found {len(environments)} environments:")

            for env in environments:
                print(f"  - ID: {env.get('id')}")
                print(f"    Name: {env.get('name')}")
                print(f"    Status: {env.get('status')}")
                print(f"    Created: {env.get('created_at')}")

                # Delete the environment
                if env.get("status") in ["running", "stopped"]:
                    env_id = env.get("id")
                    print(f"\n🗑️  Deleting environment: {env_id}")

                    delete_response = await client.delete(
                        f"https://devpocket-api.goon.vn/api/v1/environments/{env_id}",
                        headers=headers,
                        timeout=30,
                    )

                    if delete_response.status_code in [200, 204]:
                        print(f"✅ Environment {env_id} deleted successfully")
                    else:
                        print(
                            f"❌ Failed to delete environment: {delete_response.status_code} - {delete_response.text}"
                        )
        else:
            print(
                f"❌ Failed to list environments: {response.status_code} - {response.text}"
            )


if __name__ == "__main__":
    asyncio.run(delete_environment())
