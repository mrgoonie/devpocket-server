# DevPocket Server - Project Overview

## Purpose
DevPocket Server is a production-ready FastAPI backend for a mobile-first cloud IDE. It provides secure, scalable development environments accessible from mobile devices. The system manages user authentication, development environments (containers), and real-time terminal access via WebSockets.

## Key Features
- JWT Authentication with Google OAuth integration
- Role-based access control (Free, Starter, Pro, Admin)
- Environment Management (multi-template support: Python, Node.js, Go, Rust, Ubuntu)
- Real-time WebSocket terminal and log streaming
- Multi-cluster Kubernetes support
- Rate limiting and security measures
- Structured logging and monitoring

## Architecture Pattern
- Layered architecture with clear separation of concerns
- Dependency injection using FastAPI's `Depends()`
- Async/await for all I/O operations
- Service layer pattern for business logic
- Pydantic settings for configuration management
- Security middleware chain