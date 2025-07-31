# Code Style & Conventions

## Python Code Style
- **Black** for code formatting (mentioned in README)
- **Flake8** for linting (mentioned in README)
- **Type hints** for all functions (recommended in README)
- **Docstrings** for public methods (recommended in README)
- **Async/await** for I/O operations (architectural requirement)

## Naming Conventions
- **Snake_case** for variables, functions, and modules
- **PascalCase** for classes and Pydantic models
- **UPPER_CASE** for constants and environment variables
- **Descriptive names** for functions and variables

## Architecture Patterns
- **Dependency Injection**: Use FastAPI's `Depends()` system throughout
- **Service Pattern**: Business logic in service classes with `set_database()` initialization
- **Pydantic Models**: All data models inherit from BaseModel
- **Async Operations**: All database and HTTP operations are async
- **Error Handling**: Use HTTPExceptions for expected errors, structured logging for debugging

## File Organization
- **Layered Architecture**: Clear separation between API, services, models, and core
- **Single Responsibility**: Each module has a clear, focused purpose
- **Import Organization**: Standard library, third-party, local imports
- **Constants**: Environment variables managed through Pydantic Settings

## Security Best Practices
- **No secrets in code**: All secrets via environment variables
- **JWT token validation**: Consistent authentication middleware
- **Input validation**: Pydantic models for all inputs
- **SQL injection prevention**: Use parameterized queries
- **CORS configuration**: Explicit allowed origins
