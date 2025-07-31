#!/usr/bin/env python3
"""
Simple WebSocket test using websocket-client library.
"""

import json
import os
import ssl
from datetime import datetime, timedelta, timezone

import websocket
from jose import jwt


def test_websocket_simple():
    """Test WebSocket with websocket-client library"""

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
    ws_url = f"wss://devpocket-api.goon.vn/api/v1/ws/terminal/{environment_id}?token={access_token}"

    def on_message(ws, message):
        print(f"📨 Received: {message}")
        data = json.loads(message)

        if data.get("type") == "welcome":
            print("✅ WebSocket connected successfully!")
            env_info = data.get("environment", {})
            print(f"   Environment: {env_info.get('name')}")
            print(f"   Pod: {env_info.get('pod_name')}")

            # Send test command
            print("\n📝 Sending test command...")
            command_msg = {"type": "input", "data": "echo 'Hello from production!'"}
            ws.send(json.dumps(command_msg))

        elif data.get("type") == "output":
            output = data.get("data", "")
            print(f"📤 Command output:\n{output}")

            # Send ping
            print("\n🏓 Sending ping...")
            ping_msg = {"type": "ping"}
            ws.send(json.dumps(ping_msg))

        elif data.get("type") == "pong":
            print("✅ Pong received - connection is healthy!")
            print("\n🎉 WebSocket test completed successfully!")
            ws.close()

    def on_error(ws, error):
        print(f"❌ WebSocket error: {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"🔒 WebSocket closed: {close_status_code} - {close_msg}")

    def on_open(ws):
        print("🔗 WebSocket connection opened")

    print("🌐 Testing WebSocket connection to production...")
    print(f"URL: {ws_url[:80]}...")

    # Create WebSocket with SSL verification disabled for testing
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    # Disable SSL verification for testing
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE, "check_hostname": False})


if __name__ == "__main__":
    try:
        test_websocket_simple()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
