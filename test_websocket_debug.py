#!/usr/bin/env python3
"""
Debug WebSocket connection with detailed error handling.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone

import websockets
from jose import jwt


async def test_websocket_debug():
    """Test WebSocket with debug output"""

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

    environment_id = "68850093852e1ff1492d3d87"
    ws_url = (
        f"ws://localhost:8000/api/v1/ws/terminal/{environment_id}?token={access_token}"
    )

    print(f"🔍 Debug WebSocket connection...")
    print(f"   URL: {ws_url}")
    print(f"   Token: {access_token[:50]}...")

    try:
        print("   Attempting connection...")

        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")

            # Try to receive welcome message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=5)
                print(f"   Received: {message}")
            except asyncio.TimeoutError:
                print("   No welcome message received")

            return True

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"❌ Connection closed: {e}")
        print(f"   Close code: {e.code}")
        print(f"   Close reason: {e.reason}")
        return False

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Invalid status code: {e}")
        print(f"   Status: {e.status_code}")
        return False

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket error: {e}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_websocket_debug())
