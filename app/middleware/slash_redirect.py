"""
Trailing slash redirect middleware for FastAPI.

This middleware ensures that all API endpoints work with or without a trailing slash
by automatically redirecting requests to the canonical form (without trailing slash).
"""

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog

logger = structlog.get_logger(__name__)


class TrailingSlashRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle trailing slash redirects.
    
    - If a URL ends with "/" and is not the root path, redirect to the same URL without "/"
    - This ensures consistent URL structure and improves SEO
    - Preserves query parameters in the redirect
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and handle trailing slash redirects.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            Response: Either a redirect response or the original response
        """
        path = request.url.path
        
        # Skip redirect for root path and paths that don't end with slash
        if path == "/" or not path.endswith("/"):
            return await call_next(request)
        
        # Skip redirect for specific paths that should keep trailing slash
        # (like static file serving or specific API endpoints)
        skip_paths = ["/docs/", "/redoc/", "/openapi.json/"]
        if any(path.startswith(skip_path) for skip_path in skip_paths):
            return await call_next(request)
        
        # Create redirect URL without trailing slash
        redirect_path = path.rstrip("/")
        
        # Preserve query parameters
        query_string = str(request.url.query)
        if query_string:
            redirect_url = f"{redirect_path}?{query_string}"
        else:
            redirect_url = redirect_path
        
        # Log the redirect for debugging
        logger.info(
            "Redirecting trailing slash",
            original_path=path,
            redirect_path=redirect_path,
            query_string=query_string,
            method=request.method
        )
        
        # Return 301 (permanent redirect) for GET requests, 307 (temporary) for others
        status_code = 301 if request.method == "GET" else 307
        
        return RedirectResponse(
            url=redirect_url,
            status_code=status_code
        )