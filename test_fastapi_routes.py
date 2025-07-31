#!/usr/bin/env python3
"""
Test FastAPI routes to see if WebSocket route is properly registered.
"""

import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.main import app


def test_routes():
    """Print all registered routes"""
    print("🔍 FastAPI Routes:")

    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            print(f"  HTTP: {route.methods} {route.path}")
        elif hasattr(route, "path"):
            # WebSocket routes don't have methods
            print(f"  WebSocket: {route.path}")
        else:
            print(f"  Other: {route}")

    # Look specifically for WebSocket routes
    websocket_routes = [
        route
        for route in app.routes
        if hasattr(route, "path") and not hasattr(route, "methods")
    ]
    print(f"\n📡 WebSocket routes found: {len(websocket_routes)}")

    for route in websocket_routes:
        print(f"  WebSocket: {route.path}")

    # Look for our specific terminal route
    terminal_routes = [
        route
        for route in app.routes
        if hasattr(route, "path") and "terminal" in route.path
    ]
    print(f"\n💻 Terminal routes found: {len(terminal_routes)}")

    for route in terminal_routes:
        print(f"  Terminal: {route.path}")


if __name__ == "__main__":
    test_routes()
