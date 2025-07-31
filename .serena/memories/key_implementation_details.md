# Key Implementation Details

## Authentication Flow
- JWT tokens created in `auth_service.create_tokens()`
- Token validation in `middleware.auth.get_current_user()`
- Google OAuth uses `google.auth` library for token verification
- Account lockout after 5 failed attempts

## Database Architecture
- **Async MongoDB** with Motor driver
- **Critical indexes** created in `database.create_indexes()`:
  - Users: email, username (unique)
  - Environments: user_id, status
  - Metrics: time-series with TTL
- **Connection pooling** with maxPoolSize=10, minPoolSize=10

## Environment Management
- **Simulated containers** with lifecycle management
- **Container creation** stubbed in `environment_service._create_container()`
- **Resource limits** enforced via subscription-based allocation
- **Multi-cluster support** via cluster_service

## WebSocket Architecture
- **Connection management** through `WebSocketConnectionManager`
- **Authentication** via query parameter `token=jwt_token`
- **Rate limiting** per user
- **Message format**: JSON with `type` field
- **Session tracking** in database and memory for cleanup

## Security Features
- **JWT signing** with configurable SECRET_KEY
- **Password hashing** with bcrypt
- **Security headers** middleware
- **CORS configuration** for mobile app domains
- **Rate limiting** (100 req/min global, 5 req/min auth)
- **Non-root container** execution

## Configuration Management
- **Pydantic Settings** with environment variable support
- **Auto-generated SECRET_KEY** if not provided
- **Environment-specific** configurations (.env files)
- **Settings centralized** in `app.core.config.Settings`

## Service Pattern
Services require initialization:
```python
service.set_database(db)
result = await service.method()
```

## Error Handling
- **Global exception handlers** in `main.py`
- **HTTPExceptions** for expected errors
- **Structured logging** for debugging
- **Detailed error responses** in DEBUG mode
