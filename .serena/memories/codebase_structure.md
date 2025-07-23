# Codebase Structure

## Main Application Structure
```
app/
├── main.py              # FastAPI entry point with middleware
├── core/                # Core infrastructure components
│   ├── config.py        # Pydantic settings with environment variables
│   ├── database.py      # MongoDB async connection and indexing
│   ├── security.py      # JWT, password hashing, security headers
│   └── logging.py       # Structured logging with structlog
├── models/              # Pydantic data models
│   ├── user.py          # User, authentication, and subscription models
│   ├── environment.py   # Development environment and resource models
│   └── cluster.py       # Multi-cluster support models
├── services/            # Business logic layer
│   ├── auth_service.py  # User authentication, Google OAuth, lockout
│   ├── environment_service.py  # Environment lifecycle, WebSocket
│   └── cluster_service.py      # Multi-cluster management
├── api/                 # HTTP/WebSocket route handlers
│   ├── auth.py          # Authentication endpoints
│   ├── environments.py  # Environment CRUD operations
│   ├── clusters.py      # Cluster management (admin)
│   └── websocket.py     # Real-time terminal and log streaming
└── middleware/          # Request/response middleware
    ├── auth.py          # JWT token validation and user context
    └── rate_limiting.py # In-memory rate limiting
```

## Configuration Files
- `requirements.txt` - Python dependencies
- `docker-compose.yaml` - Multi-service Docker setup
- `Dockerfile` - Application container definition
- `nginx.conf` - Reverse proxy configuration
- `start.sh` - Development startup script
- `CLAUDE.md` - Development guidelines and commands