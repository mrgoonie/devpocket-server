#!/usr/bin/env python3
"""
Test WebSocket connection to a created environment
"""

import asyncio
import json
import sys
from pathlib import Path

import websockets

# Load environment variables
from dotenv import load_dotenv

load_dotenv(".env.prod")

# Add the app directory to Python path
app_dir = Path(__file__).parent
sys.path.insert(0, str(app_dir))

try:
    from datetime import datetime, timedelta

    from jose import jwt
    from motor.motor_asyncio import AsyncIOMotorClient

    from app.core.config import settings
    from app.services.auth_service import auth_service
    from app.services.environment_service import environment_service
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def create_test_token():
    """Create a test JWT token for WebSocket auth"""
    # Create test user payload
    payload = {
        "sub": "c1e89f47-f92c-4dea-91bf-d8cfcc54cf47",  # User ID from our test
        "username": "testuser",
        "email": "test@devpocket.io",
        "exp": datetime.utcnow() + timedelta(hours=1),
    }

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


async def get_running_environment():
    """Get a running environment for testing"""
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    environment_service.set_database(db)

    # Find a running environment
    env_doc = await db.environments.find_one(
        {"status": "running", "user_id": "c1e89f47-f92c-4dea-91bf-d8cfcc54cf47"}
    )

    client.close()

    if env_doc:
        return env_doc["_id"], env_doc["name"]
    return None, None


async def test_websocket_connection():
    """Test WebSocket connection to environment terminal"""

    print("🧪 Testing WebSocket Connection to Environment")
    print("=" * 50)

    # Get running environment
    env_id, env_name = await get_running_environment()
    if not env_id:
        print("❌ No running environment found for testing")
        return False

    print(f"🎯 Target environment: {env_name} ({env_id})")

    # Create test token
    token = await create_test_token()
    print(f"🔐 Created test JWT token")

    # WebSocket URL
    ws_url = f"ws://localhost:8000/api/v1/ws/terminal/{env_id}?token={token}"
    print(f"🔗 WebSocket URL: {ws_url}")

    try:
        print("\n⏳ Connecting to WebSocket...")

        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")

            # Send a ping message
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            print("📤 Sent ping message")

            # Wait for pong response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"📥 Received response: {response_data}")

                if response_data.get("type") == "pong":
                    print("✅ Ping/Pong successful!")

            except asyncio.TimeoutError:
                print("⏰ No response received within 5 seconds")

            # Send a terminal command
            command_message = {
                "type": "input",
                "data": "echo 'Hello from WebSocket terminal!'\n",
            }
            await websocket.send(json.dumps(command_message))
            print("📤 Sent terminal command")

            # Wait for command response
            try:
                for i in range(3):  # Wait for up to 3 messages
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    response_data = json.loads(response)
                    print(f"📥 Terminal output: {response_data}")

            except asyncio.TimeoutError:
                print("⏰ No terminal response received")

            print("✅ WebSocket test completed!")
            return True

    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False


async def main():
    """Main test function"""
    try:
        success = await test_websocket_connection()
        if success:
            print("\n🎉 WebSocket test passed!")
        else:
            print("\n❌ WebSocket test failed!")
            sys.exit(1)

    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test cancelled by user")
        sys.exit(0)
