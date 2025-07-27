#!/usr/bin/env python3
"""
Test production API authentication and environment access.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt


async def test_production_api():
    """Test production API"""

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

    print("🔍 Testing production API authentication...")

    async with httpx.AsyncClient() as client:
        # Test user endpoint
        print("\n1. Testing /api/v1/auth/me endpoint...")
        try:
            response = await client.get(
                "https://devpocket-api.goon.vn/api/v1/auth/me",
                headers=headers,
                timeout=30,
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                user_data = response.json()
                print(f"   ✅ User authenticated: {user_data.get('username')}")
                print(f"   Email: {user_data.get('email')}")
                print(f"   Subscription: {user_data.get('subscription_plan')}")
            else:
                print(f"   ❌ Authentication failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")

        # Test environment endpoint
        print("\n2. Testing /api/v1/environments endpoint...")
        env_id = "68850093852e1ff1492d3d87"
        try:
            response = await client.get(
                f"https://devpocket-api.goon.vn/api/v1/environments/{env_id}",
                headers=headers,
                timeout=30,
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                env_data = response.json()
                print(f"   ✅ Environment found: {env_data.get('name')}")
                print(f"   Status: {env_data.get('status')}")
                print(f"   Namespace: {env_data.get('namespace')}")
                print(f"   Pod name: {env_data.get('pod_name')}")
            else:
                print(f"   ❌ Environment not found: {response.text}")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")

        # Test WebSocket upgrade request
        print("\n3. Testing WebSocket upgrade request...")
        ws_url = f"https://devpocket-api.goon.vn/api/v1/ws/terminal/{env_id}?token={access_token}"
        try:
            # Send a regular HTTP request to the WebSocket endpoint to see the response
            response = await client.get(
                ws_url,
                headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Version": "13",
                    "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                },
                timeout=30,
            )
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            if response.status_code != 101:
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_production_api())
