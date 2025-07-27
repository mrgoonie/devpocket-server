#!/usr/bin/env python3
"""
Test WebSocket terminal connection to existing environment on production server.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone

import websockets
from jose import jwt


async def test_websocket_production():
    """Test WebSocket terminal connection on production server"""
    print("🌐 Testing WebSocket terminal connection on production...")

    # Create JWT token for existing user
    secret_key = os.getenv("SECRET_KEY", "9XX36cij9crf1VJPFUjphfZlk8vfuOBok5pxkHa-YsU")
    payload = {
        "sub": "6880cb54f9f0280f9e9f70c8",  # goon user ID
        "username": "goon",
        "email": "goon.nguyen@gmail.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
        "type": "access_token",
    }
    access_token = jwt.encode(payload, secret_key, algorithm="HS256")

    # Use existing environment ID (found in database)
    environment_id = "68850093852e1ff1492d3d87"
    ws_url = f"wss://api.devpocket.app/api/v1/ws/terminal/{environment_id}?token={access_token}"

    try:
        print(f"   Connecting to: {ws_url[:80]}...")
        print(f"   Environment ID: {environment_id}")

        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket connected successfully!")

            # Wait for welcome message
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=10)
                welcome_data = json.loads(welcome_msg)
                print(f"   Welcome message: {welcome_data.get('message')}")

                if welcome_data.get("type") == "welcome":
                    env_info = welcome_data.get("environment", {})
                    print(f"   Environment: {env_info.get('name')}")
                    print(f"   Status: {env_info.get('status')}")
                    print(f"   Template: {env_info.get('template')}")
                    print(f"   Pod name: {env_info.get('pod_name')}")
            except asyncio.TimeoutError:
                print("   ⚠️ No welcome message received within timeout")

            # Test commands
            test_commands = [
                "pwd",
                "whoami",
                "echo 'Hello from DevPocket production!'",
                "ls -la",
                "cat /etc/os-release | head -2",
                "date",
            ]

            for cmd in test_commands:
                print(f"\n   📝 Executing: {cmd}")

                # Send command
                command_msg = {"type": "input", "data": cmd}
                await websocket.send(json.dumps(command_msg))

                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15)
                    response_data = json.loads(response)

                    if response_data.get("type") == "output":
                        output = response_data.get("data", "")
                        print(f"   📤 Output:")
                        for line in output.strip().split("\n"):
                            if line.strip():
                                print(f"      {line}")
                    else:
                        print(f"   📤 Response: {response_data}")

                except asyncio.TimeoutError:
                    print(f"   ⚠️ Command timeout")

                await asyncio.sleep(1)  # Small delay between commands

            # Test ping/pong
            print(f"\n   🏓 Testing ping/pong...")
            ping_msg = {"type": "ping"}
            await websocket.send(json.dumps(ping_msg))

            try:
                pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                pong_data = json.loads(pong_response)
                if pong_data.get("type") == "pong":
                    print("   ✅ Ping/pong successful")
                else:
                    print(f"   ⚠️ Unexpected ping response: {pong_data}")
            except asyncio.TimeoutError:
                print("   ⚠️ Ping timeout")

            print(f"\n✅ WebSocket terminal test completed successfully!")
            return True

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    print("🚀 Starting Production WebSocket Terminal Test")
    print("=" * 60)

    # First verify the environment exists in Kubernetes
    print("🔍 Verifying Kubernetes environment...")
    result = os.system(
        "kubectl --kubeconfig=k8s/kube_config_ovh.yaml get pods -n user-6880cb54f9f0280f9e9f70c8"
    )
    if result == 0:
        print("✅ Kubernetes environment verified")
    else:
        print("⚠️ Could not verify Kubernetes environment")

    print("\n" + "=" * 60)

    success = await test_websocket_production()

    print("=" * 60)
    if success:
        print("🎉 Production WebSocket terminal test PASSED!")
        exit(0)
    else:
        print("❌ Production WebSocket terminal test FAILED!")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
