from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class NoOpRateLimitMiddleware(BaseHTTPMiddleware):
    """No-op rate limiting middleware for tests"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        return response
