# Suggested Commands

## Development Setup
```bash
# Quick start with Docker
./start.sh

# Manual setup - install dependencies
pip install -r requirements.txt

# Start databases only
docker-compose up -d mongo redis

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker Commands
```bash
# Build and start all services
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f devpocket-api

# Scale API instances
docker-compose up -d --scale devpocket-api=3

# Restart specific service
docker-compose restart devpocket-api

# Stop all services
docker-compose down
```

## Database Operations
```bash
# Access MongoDB directly
docker-compose exec mongo mongosh devpocket

# Reset database (destructive)
docker-compose down -v
docker-compose up -d mongo
```

## Health Checks & Testing
```bash
# Check API health
curl http://localhost:8000/health

# Access interactive docs
open http://localhost:8000/docs
open http://localhost:8000/redoc

# Run tests (when available)
pytest
pytest --cov=app --cov-report=html
```

## Code Quality (when configured)
```bash
# Code formatting
black app/

# Linting
flake8 app/

# Type checking (if mypy configured)
mypy app/
```

## System Utilities (macOS/Darwin)
```bash
# File operations
ls -la
find . -name "*.py"
grep -r "pattern" app/

# Git operations
git status
git log --oneline
git diff

# Process monitoring
ps aux | grep python
top -p $(pgrep python)
```