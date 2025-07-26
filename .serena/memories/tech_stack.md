# Tech Stack

## Core Framework
- **FastAPI** (0.110.0) - Main web framework
- **Uvicorn** - ASGI server with standard extras
- **Python 3.11+** - Programming language

## Database & Storage
- **MongoDB** - Primary database (via Motor async driver)
- **Redis** - Caching and session management
- **Motor** (3.3.2) - Async MongoDB driver
- **PyMongo** (4.6.1) - MongoDB driver

## Authentication & Security
- **python-jose** - JWT token handling
- **passlib[bcrypt]** - Password hashing
- **google-auth** - Google OAuth integration
- **cryptography** - Cryptographic operations

## Infrastructure & Deployment
- **Docker** & **Docker Compose** - Containerization
- **Kubernetes** (29.0.0) - Container orchestration
- **Nginx** - Reverse proxy and load balancing
- **Gunicorn** - WSGI server for production

## Development & Monitoring
- **Pydantic** - Data validation and settings
- **structlog** - Structured logging
- **httpx** - Async HTTP client
- **websockets** - WebSocket support
- **aiofiles** - Async file operations
