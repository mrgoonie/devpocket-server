from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import structlog

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.logging import configure_logging
from app.core.security import SecurityHeaders
from app.middleware.rate_limiting import RateLimitMiddleware
from app.api import auth, environments, websocket, clusters

# Configure logging
logger = configure_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting DevPocket API server", version="1.0.0")
    
    try:
        await connect_to_mongo()
        logger.info("Database connected successfully")
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down DevPocket API server")
    await close_mongo_connection()
    logger.info("Database connection closed")

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="""
    **DevPocket API** - The mobile-first cloud IDE backend
    
    ## Features
    
    * **User Authentication** - JWT and Google OAuth support
    * **Environment Management** - Create, manage, and connect to development environments
    * **WebSocket Terminal** - Real-time terminal access to your environments
    * **Resource Monitoring** - Track CPU, memory, and storage usage
    * **Multi-tenant** - Secure isolation between users
    
    ## Authentication
    
    Most endpoints require authentication using JWT tokens. Include the token in the Authorization header:
    ```
    Authorization: Bearer <your-jwt-token>
    ```
    
    ## Subscription Plans
    
    - **Free**: 1 environment, basic resources
    - **Starter**: 3 environments, increased resources  
    - **Pro**: 10 environments, premium resources
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG or not settings.is_production else None,
    redoc_url="/redoc" if settings.DEBUG or not settings.is_production else None,
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    headers = SecurityHeaders.get_security_headers()
    for name, value in headers.items():
        response.headers[name] = value
    
    return response

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    calls=100,  # 100 requests per minute
    period=60
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

app.include_router(
    environments.router,
    prefix="/api/v1/environments",
    tags=["Environments"],
)

app.include_router(
    websocket.router,
    prefix="/api/v1/ws",
    tags=["WebSocket"],
)

app.include_router(
    clusters.router,
    prefix="/api/v1/clusters",
    tags=["Clusters"],
)

# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Validation error",
        path=request.url.path,
        method=request.method,
        errors=exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "error": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"}
        )

# Health check endpoints
@app.get("/", include_in_schema=False)
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time()
    }

@app.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    try:
        from app.core.database import db
        
        # Check database connection
        await db.client.admin.command('ping')
        
        return {
            "status": "ready",
            "checks": {
                "database": "healthy"
            }
        }
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "error": str(e)
            }
        )

@app.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {"status": "alive"}

# API Information
@app.get("/api/v1/info")
async def api_info():
    """Get API information"""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "features": {
            "authentication": True,
            "google_oauth": bool(settings.GOOGLE_CLIENT_ID),
            "websockets": True,
            "rate_limiting": True,
            "metrics": True
        },
        "limits": {
            "free_environments": 1,
            "starter_environments": 3,
            "pro_environments": 10
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["default"],
            },
        }
    )