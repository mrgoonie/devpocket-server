from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Optional
import time
import structlog
import os
from app.core.config import settings

logger = structlog.get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware"""

    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # Number of calls allowed
        self.period = period  # Time period in seconds
        self.requests: Dict[str, list] = {}
        # Check if we're in a test environment
        self.is_test_env = os.environ.get("TESTING", "false").lower() == "true"

    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"

    def is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited"""
        # Skip rate limiting in test environment
        if self.is_test_env:
            return False
            
        now = time.time()

        # Initialize client if not exists
        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Remove old requests outside the time window
        self.requests[client_ip] = [
            req_time
            for req_time in self.requests[client_ip]
            if now - req_time < self.period
        ]

        # Check if limit exceeded
        if len(self.requests[client_ip]) >= self.calls:
            return True

        # Add current request
        self.requests[client_ip].append(now)
        return False

    async def dispatch(self, request: Request, call_next):
        client_ip = self.get_client_ip(request)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Check rate limit
        if self.is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": self.period,
                },
                headers={"Retry-After": str(self.period)},
            )

        response = await call_next(request)
        return response


class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections"""

    def __init__(self, max_connections: int = 5, max_messages_per_minute: int = 100):
        self.max_connections = max_connections
        self.max_messages_per_minute = max_messages_per_minute
        self.connections: Dict[str, int] = {}
        self.messages: Dict[str, list] = {}

    def check_connection_limit(self, user_id: str) -> bool:
        """Check if user has too many WebSocket connections"""
        current_connections = self.connections.get(user_id, 0)
        return current_connections < self.max_connections

    def add_connection(self, user_id: str):
        """Add a WebSocket connection for user"""
        self.connections[user_id] = self.connections.get(user_id, 0) + 1

    def remove_connection(self, user_id: str):
        """Remove a WebSocket connection for user"""
        if user_id in self.connections:
            self.connections[user_id] = max(0, self.connections[user_id] - 1)
            if self.connections[user_id] == 0:
                del self.connections[user_id]

    def check_message_rate(self, user_id: str) -> bool:
        """Check if user is sending messages too fast"""
        now = time.time()

        # Initialize user messages if not exists
        if user_id not in self.messages:
            self.messages[user_id] = []

        # Remove old messages outside the time window
        self.messages[user_id] = [
            msg_time
            for msg_time in self.messages[user_id]
            if now - msg_time < 60  # 1 minute window
        ]

        # Check if limit exceeded
        if len(self.messages[user_id]) >= self.max_messages_per_minute:
            return False

        # Add current message
        self.messages[user_id].append(now)
        return True


# Global rate limiter instances
websocket_rate_limiter = WebSocketRateLimiter()
