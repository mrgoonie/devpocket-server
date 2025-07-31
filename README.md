# 📱 DevPocket Server

> **The world's first mobile-native cloud IDE backend**

DevPocket Server is a production-ready Python FastAPI backend that powers the DevPocket mobile-first cloud IDE. It provides secure, scalable development environments accessible from any mobile device.

- **DevPocker Mobile App**: https://github.com/mrgoonie/devpocket-app

## ✨ Features

### 🔐 Authentication & Security
- **JWT Authentication** with secure token management
- **Google OAuth** integration for seamless sign-in
- **Role-based access control** (Free, Starter, Pro, Admin)
- **Rate limiting** and DDoS protection
- **Security headers** and CORS configuration
- **Account lockout** after failed login attempts

### 🖥️ Environment Management
- **Multi-template support** (Python, Node.js, Go, Rust, Ubuntu)
- **Resource limits** based on subscription plans
- **Real-time monitoring** (CPU, memory, storage usage)
- **Environment lifecycle** management (create, start, stop, delete)
- **Persistent storage** for development workspaces

### 🌐 WebSocket Support
- **Real-time terminal access** to environments
- **Live log streaming** from containers
- **Connection management** with automatic cleanup
- **Rate limiting** for WebSocket connections

### 📊 Monitoring & Observability
- **Structured logging** with JSON output
- **Health checks** for Kubernetes deployments
- **Metrics collection** with Prometheus integration
- **Database indexing** for optimal performance

### 🚀 Production Ready
- **Docker containerization** with multi-stage builds
- **Docker Compose** setup with all dependencies
- **Nginx reverse proxy** with SSL termination
- **MongoDB** with replica set support
- **Redis** for caching and session management

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐
│   Mobile App    │────│   Nginx Proxy    │────│  FastAPI App   │
│   (Flutter)     │    │  (Load Balancer) │    │   (Python)     │
└─────────────────┘    └──────────────────┘    └────────────────┘
                                                        │
                        ┌──────────────────┐           │
                        │   Environment    │←──────────┤
                        │   Orchestrator   │           │
                        │  (Kubernetes)    │           │
                        └──────────────────┘           │
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐
│   MongoDB       │────│      Redis       │────│   Prometheus   │
│  (Database)     │    │    (Cache)       │    │  (Metrics)     │
└─────────────────┘    └──────────────────┘    └────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- MongoDB 7.0+
- Redis 7.0+

### 1. Clone the Repository

```bash
git clone <repository-url>
cd devpocket-server
```

### 2. Environment Configuration

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=devpocket

# Security
SECRET_KEY=your-super-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Application
ENVIRONMENT=development
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

#### Database Seeding
```bash
# Add a default cluster credentials to database
export ENV_FILE=.env.prod
python3 scripts/add_default_ovh_cluster.py

# Show available default templates (no database required)
python3 scripts/show_default_templates.py

# Seed default environment templates (requires MongoDB)
python3 scripts/seed_templates.py

# Force reseed templates (removes existing ones first)
python3 scripts/seed_templates.py --force
```

### 3. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f devpocket-api
```

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Access API documentation
open http://localhost:8000/docs
```

## 🔧 Development Setup

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Database Services**
   ```bash
   docker-compose up -d mongo redis
   ```

3. **Run the Application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `DATABASE_NAME` | `devpocket` | Database name |
| `SECRET_KEY` | *generated* | JWT secret key |
| `GOOGLE_CLIENT_ID` | `None` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | `None` | Google OAuth client secret |
| `DEBUG` | `False` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ALLOWED_ORIGINS` | `["http://localhost:3000"]` | CORS allowed origins |

## 📱 API Documentation

### Authentication Endpoints

```http
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/google
GET  /api/v1/auth/me
POST /api/v1/auth/logout
```

### Environment Management

```http
GET    /api/v1/environments
POST   /api/v1/environments
GET    /api/v1/environments/{id}
DELETE /api/v1/environments/{id}
POST   /api/v1/environments/{id}/start
POST   /api/v1/environments/{id}/stop
GET    /api/v1/environments/{id}/metrics
```

### WebSocket Endpoints

```http
WS /api/v1/ws/terminal/{environment_id}
WS /api/v1/ws/logs/{environment_id}
```

### Example Usage

#### Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "email": "dev@example.com",
    "password": "SecurePass123!",
    "full_name": "Developer User"
  }'
```

#### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "developer",
    "password": "SecurePass123!"
  }'
```

#### Create Environment

```bash
curl -X POST http://localhost:8000/api/v1/environments \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-python-env",
    "template": "python"
  }'
```

#### WebSocket Terminal Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/terminal/env-123?token=your-jwt-token');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Terminal output:', data);
};

ws.send(JSON.stringify({
    type: 'input',
    data: 'ls -la\n'
}));
```

## 🐳 Docker Deployment

### Local Development with Docker Compose

```bash
# Build and start all services
docker-compose -f docker-compose.yaml up -d

# Scale API instances
docker-compose up -d --scale devpocket-api=3

# Update containers
docker-compose pull
docker-compose up -d
```

### Production Kubernetes Deployment

The project includes comprehensive Kubernetes manifests and automated CI/CD:

```bash
# Quick deployment
./scripts/deploy.sh

# Deploy specific version
./scripts/deploy.sh v1.2.3

# Update secrets
./scripts/update-secrets.sh
```

#### Automated Deployment
- **GitHub Actions**: Automatic build and deploy on push to `main`
- **Docker Registry**: `digitop/devpocket-api` on Docker Hub
- **Versioning**: Semantic versioning with Git tags
- **Health Checks**: Automated readiness and liveness probes
- **Scaling**: Horizontal Pod Autoscaler (3-10 replicas)

See [k8s/README.md](k8s/README.md) for detailed Kubernetes deployment guide.

## 🔒 Security Best Practices

### Implemented Security Measures

1. **Authentication & Authorization**
   - JWT tokens with configurable expiration
   - Google OAuth integration
   - Role-based access control
   - Account lockout after failed attempts

2. **API Security**
   - Rate limiting (100 req/min global, 5 req/min auth)
   - Request size limits (10MB)
   - CORS configuration
   - Security headers (CSP, HSTS, etc.)

3. **Data Protection**
   - Password hashing with bcrypt
   - Secure token generation
   - Database input validation
   - Environment variable secrets

4. **Infrastructure Security**
   - Non-root container user
   - Network isolation
   - Health checks
   - Graceful shutdown handling

### Security Recommendations

1. **Production Secrets**
   ```bash
   # Generate secure secret key
   python -c "import secrets; print(secrets.token_urlsafe(32))"

   # Use environment variables for all secrets
   export SECRET_KEY="your-secure-key"
   export GOOGLE_CLIENT_SECRET="your-oauth-secret"
   ```

2. **Database Security**
   ```bash
   # Enable MongoDB authentication
   MONGODB_URL=mongodb://username:password@mongo:27017/devpocket?authSource=admin
   ```

3. **SSL/TLS Configuration**
   ```nginx
   server {
       listen 443 ssl http2;
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       # ... additional SSL configuration
   }
   ```

## 📊 Monitoring & Observability

### Health Checks

- **Health**: `GET /health` - Basic service health
- **Readiness**: `GET /health/ready` - Database connectivity
- **Liveness**: `GET /health/live` - Service responsiveness

### Logging

Structured logging with configurable formats:

```python
# JSON logging for production
LOG_FORMAT=json

# Console logging for development
LOG_FORMAT=console
```

### Metrics

Built-in metrics collection for:
- Request counts and latencies
- Database connection pools
- Environment resource usage
- WebSocket connections
- Error rates

### Prometheus Integration

```yaml
# Add to docker-compose.yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

## 🚀 Performance Optimization

### Database Optimization

1. **Indexes**
   ```javascript
   // Automatically created indexes
   db.users.createIndex({ "email": 1 }, { unique: true })
   db.environments.createIndex({ "user_id": 1, "status": 1 })
   ```

2. **Connection Pooling**
   ```python
   # MongoDB connection pool
   client = AsyncIOMotorClient(
       MONGODB_URL,
       maxPoolSize=10,
       minPoolSize=10
   )
   ```

### Application Optimization

1. **Async/Await**
   - All I/O operations are asynchronous
   - Non-blocking database calls
   - Concurrent request handling

2. **Caching**
   - Redis for session storage
   - In-memory rate limiting
   - Connection pooling

3. **Resource Limits**
   ```yaml
   # Container resource limits
   resources:
     limits:
       memory: "512Mi"
       cpu: "500m"
     requests:
       memory: "256Mi"
       cpu: "250m"
   ```

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v
```

### Test Categories

- **Unit Tests**: Individual function testing
- **Integration Tests**: Database and service integration
- **API Tests**: HTTP endpoint testing
- **WebSocket Tests**: Real-time connection testing

### Example Test

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_register_user():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/v1/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        })
    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
```

## 🔄 CI/CD Pipeline

### GitHub Actions Example

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx
      - name: Run tests
        run: pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          # Your deployment script here
          echo "Deploying to production..."
```

## 🤝 Contributing

### Development Workflow

1. **Fork & Clone**
   ```bash
   git clone <your-fork-url>
   cd devpocket-server
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Install Development Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Make Changes & Test**
   ```bash
   pytest
   black app/  # Code formatting
   flake8 app/ # Linting
   ```

5. **Commit & Push**
   ```bash
   git commit -m "Add amazing feature"
   git push origin feature/amazing-feature
   ```

6. **Create Pull Request**

### Code Style

- **Black** for code formatting
- **Flake8** for linting
- **Type hints** for all functions
- **Docstrings** for public methods
- **Async/await** for I/O operations

### Commit Convention

```
feat: add user authentication
fix: resolve database connection issue
docs: update API documentation
test: add environment tests
refactor: optimize database queries
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Documentation

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Architecture**: See `docs/` folder

### Getting Help

1. **Issues**: Create a GitHub issue for bugs
2. **Discussions**: Use GitHub Discussions for questions
3. **Discord**: Join our developer community
4. **Email**: support@devpocket.io

### Troubleshooting

#### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check MongoDB status
   docker-compose logs mongo

   # Verify connection string
   echo $MONGODB_URL
   ```

2. **Import Errors**
   ```bash
   # Rebuild containers
   docker-compose build --no-cache

   # Check Python path
   python -c "import sys; print(sys.path)"
   ```

3. **WebSocket Connection Issues**
   ```bash
   # Check nginx configuration
   docker-compose logs nginx

   # Verify WebSocket headers
   curl -H "Upgrade: websocket" http://localhost:8000/api/v1/ws/terminal/test
   ```

## 🚀 Roadmap

### v1.1 (Current)
- [x] JWT Authentication
- [x] Google OAuth
- [x] Environment Management
- [x] WebSocket Terminal
- [x] Docker Deployment

### v1.2 (Next)
- [ ] Kubernetes Integration
- [ ] File Upload/Download
- [ ] Environment Sharing
- [ ] Usage Analytics
- [ ] API Rate Limiting Per User

### v2.0 (Future)
- [ ] Multi-region Deployment
- [ ] Environment Templates Store
- [ ] AI-powered Code Assistance
- [ ] Team Collaboration Features
- [ ] Advanced Monitoring Dashboard

---

**Built with ❤️ for the mobile-first developer community**

*DevPocket - Code Anywhere, Build Everywhere* 📱💻
