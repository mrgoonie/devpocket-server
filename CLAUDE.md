# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DevPocket Server is a production-ready FastAPI backend for a mobile-first cloud IDE. It provides secure, scalable development environments accessible from mobile devices. The system manages user authentication, development environments (containers), and real-time terminal access via WebSockets.

## Architecture

The application follows a layered architecture with clear separation of concerns:

```
app/
├── main.py              # FastAPI application entry point with middleware
├── core/                # Core infrastructure components
│   ├── config.py        # Pydantic settings with environment variables
│   ├── database.py      # MongoDB async connection and indexing
│   ├── security.py      # JWT, password hashing, security headers
│   └── logging.py       # Structured logging with structlog
├── models/              # Pydantic data models
│   ├── user.py          # User, authentication, and subscription models
│   └── environment.py   # Development environment and resource models
├── services/            # Business logic layer
│   ├── auth_service.py  # User authentication, Google OAuth, account lockout
│   └── environment_service.py  # Environment lifecycle, WebSocket sessions
├── api/                 # HTTP/WebSocket route handlers
│   ├── auth.py          # Authentication endpoints (register, login, OAuth)
│   ├── environments.py  # Environment CRUD operations
│   └── websocket.py     # Real-time terminal and log streaming
└── middleware/          # Request/response middleware
    ├── auth.py          # JWT token validation and user context
    └── rate_limiting.py # In-memory rate limiting
```

## Key Architectural Patterns

**Dependency Injection**: FastAPI's `Depends()` system is used throughout for database connections, authentication, and service injection. Services require `set_database()` calls to initialize database connections.

**Async/Await**: All I/O operations are asynchronous using Motor (async MongoDB driver) and httpx for external API calls.

**Service Layer Pattern**: Business logic is separated into service classes (`auth_service`, `environment_service`) that are injected into API routes.

**Settings Management**: Configuration uses Pydantic Settings with environment variable support. Settings are centralized in `app.core.config.Settings`.

**Security Middleware Chain**: Multiple middleware layers handle security (rate limiting, CORS, security headers) before requests reach route handlers.

## Development Commands

### Local Development
```bash
# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Install dependencies
pip install -r requirements.txt

# Start databases only
docker-compose up -d mongo redis

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Add a default cluster credentials to database
ENV_FILE=.env.prod python3 scripts/add_default_ovh_cluster.py
```

### Docker Development
```bash
# Quick start with provided script
./start.sh

# Manual Docker commands
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f devpocket-api

# Scale API instances
docker-compose up -d --scale devpocket-api=3

# Restart specific service
docker-compose restart devpocket-api
```

### Database Operations
```bash
# Access MongoDB directly
docker-compose exec mongo mongosh devpocket

# View database logs
docker-compose logs mongo

# Reset database (destructive)
docker-compose down -v
docker-compose up -d mongo
```

### Testing & Development
```bash
# Run linting (when configured)
black app/
flake8 app/

# Check API health
curl http://localhost:8000/health

# Access interactive documentation
open http://localhost:8000/docs
```

### Database Seeding
```bash
# Add a default cluster credentials to database
ENV_FILE=.env.prod python3 scripts/add_default_ovh_cluster.py

# Show available default templates (no database required)
python3 scripts/show_default_templates.py

# Show templates with production config
ENV_FILE=.env.prod python3 scripts/show_default_templates.py

# Seed default environment templates (requires MongoDB)
python3 scripts/seed_templates.py

# Seed with production config
ENV_FILE=.env.prod python3 scripts/seed_templates.py

# Force reseed templates (removes existing ones first)
python3 scripts/seed_templates.py --force
```

### Release Management

This project uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) for automated versioning and releases.

```bash
# Check what the next version would be (dry run)
semantic-release version --noop --print

# Create a new release locally (for testing)
semantic-release version

# Preview changelog for next version
semantic-release changelog --unreleased
```

#### Commit Message Format

Follow [Conventional Commits](https://conventionalcommits.org/) for automatic version bumping:

- `feat:` - New features (minor version bump)
- `fix:` - Bug fixes (patch version bump)  
- `perf:` - Performance improvements (patch version bump)
- `BREAKING CHANGE:` - Breaking changes (major version bump)
- `chore:`, `docs:`, `style:`, `refactor:`, `test:` - No version bump

#### Automated Release Process

Releases are automatically created when commits are pushed to:
- `main` branch - Creates production releases
- `dev/*` branches - Creates pre-release versions with `-dev` suffix

The release workflow:
1. Analyzes commit messages since last release
2. Determines next version number using semantic versioning
3. Updates version in `pyproject.toml`
4. Generates/updates `CHANGELOG.md`
5. Creates Git tag and GitHub release
6. Builds and deploys Docker image to production (main branch only)

## Important Implementation Details

**Authentication Flow**: JWT tokens are created in `auth_service.create_tokens()` and validated in `middleware.auth.get_current_user()`. Google OAuth uses `google.auth` library for token verification.

**Environment Management**: Environments are simulated containers with lifecycle management. The actual container creation is stubbed in `environment_service._create_container()` - this would integrate with Kubernetes in production.

**WebSocket Architecture**: WebSocket connections are managed through `WebSocketConnectionManager` with rate limiting per user. Terminal sessions are tracked in database and memory for cleanup.

**Database Indexes**: Critical indexes are created in `database.create_indexes()` for users (email, username), environments (user_id, status), and metrics (time-series data with TTL).

**Resource Limits**: Subscription-based resource allocation is enforced in `environment_service._get_default_resources()` and `_check_user_limits()`.

**Error Handling**: Global exception handlers in `main.py` provide structured error responses. HTTPExceptions are used for expected errors, with detailed logging for debugging.

**Security Features**: Account lockout after 5 failed attempts, rate limiting middleware, security headers, CORS configuration, and non-root container execution.

## Configuration

Environment variables are managed through `.env` files and Pydantic Settings:
- `MONGODB_URL`: Database connection string
- `SECRET_KEY`: JWT signing key (auto-generated if not provided)
- `GOOGLE_CLIENT_ID/SECRET`: OAuth credentials
- `DEBUG`: Enables detailed error responses and API docs
- `ALLOWED_ORIGINS`: CORS configuration for mobile app domains

## WebSocket Usage

WebSocket endpoints expect authentication via query parameter `token`:
```
ws://localhost:8000/api/v1/ws/terminal/{environment_id}?token=jwt_token
```

Message format is JSON with `type` field:
- `{"type": "input", "data": "command\n"}` - Terminal input
- `{"type": "resize", "cols": 80, "rows": 24}` - Terminal resize
- `{"type": "ping"}` - Keepalive (responds with pong)

## Services Architecture

Services follow a pattern where they must be initialized with database connection:
```python
service.set_database(db)
result = await service.method()
```

This pattern allows for dependency injection while maintaining clean separation between database access and business logic.

## Production Deployment

The application includes production-ready Docker configuration with:
- Multi-stage builds for smaller images
- Non-root user execution
- Health checks for orchestrators
- Nginx reverse proxy with rate limiting
- MongoDB with authentication and indexing
- Redis for caching and rate limiting

## Development rules

- always create/update `./plans/<FEATURE_NAME>_TASKS.md` to manage todos in every feature implementation/progress, update status of this file after finish each task
- ask questions for clarification of uncleared requests
- implement error catch handler and validation carefully
- follow security best practices
- focus on human-readable & developer-friendly when writing code
- high standard of user experience
- run app to check if it works, fix all issues if any
- commit the code on the current branch after every task implemented (if it works)
- Keep commits focused on the actual code changes
- NEVER automatically add AI attribution signatures like:
  "🤖 Generated with [Claude Code]"
  "Co-Authored-By: Claude noreply@anthropic.com"
  Any AI tool attribution or signature
- Create clean, professional commit messages without AI references. Use conventional commit format.
- use `context7` MCP tool for documentation during implementation