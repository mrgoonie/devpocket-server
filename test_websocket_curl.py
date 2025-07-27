#!/usr/bin/env python3
"""
Test WebSocket connection using curl to debug connection issues.
"""

import os
import subprocess
from datetime import datetime, timedelta, timezone

from jose import jwt


def test_websocket_curl():
    """Test WebSocket with curl to debug connection issues"""

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

    print("🌐 Testing WebSocket connection with curl...")
    print(f"URL: {ws_url[:80]}...")

    # Test with curl to see if we can establish WebSocket connection
    curl_cmd = [
        "curl",
        "-v",  # verbose
        "-i",  # include headers
        "--http1.1",
        "--no-buffer",
        "--header",
        "Connection: Upgrade",
        "--header",
        "Upgrade: websocket",
        "--header",
        "Sec-WebSocket-Version: 13",
        "--header",
        "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==",
        "--max-time",
        "30",
        ws_url.replace("wss://", "https://"),  # Use HTTPS for curl test
    ]

    try:
        print("\n📡 Running curl command...")
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)

        print("=== CURL OUTPUT ===")
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")

    except subprocess.TimeoutExpired:
        print("❌ curl command timed out")
    except Exception as e:
        print(f"❌ curl command failed: {e}")

    # Also test direct HTTP connection to the API
    print("\n🔍 Testing HTTP API connection...")
    api_cmd = [
        "curl",
        "-v",
        "-H",
        f"Authorization: Bearer {access_token}",
        "-H",
        "Content-Type: application/json",
        "--max-time",
        "10",
        f"https://devpocket-api.goon.vn/api/v1/environments/{environment_id}",
    ]

    try:
        result = subprocess.run(api_cmd, capture_output=True, text=True, timeout=15)
        print("=== API TEST OUTPUT ===")
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")

    except Exception as e:
        print(f"❌ API test failed: {e}")


if __name__ == "__main__":
    test_websocket_curl()
