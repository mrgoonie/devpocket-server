import secrets
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "DevPocket API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Security settings
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database settings
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "devpocket"

    # Google OAuth settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"

    # CORS settings
    ALLOWED_ORIGINS: Union[
        List[str], str
    ] = "http://localhost:3000,http://localhost:3001"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Container settings
    CONTAINER_REGISTRY: str = "docker.io"
    CONTAINER_CPU_LIMIT: str = "1000m"
    CONTAINER_MEMORY_LIMIT: str = "2Gi"
    CONTAINER_STORAGE_LIMIT: str = "10Gi"

    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"

    # Email settings
    RESEND_API_KEY: Optional[str] = None
    EMAIL_FROM: str = "noreply@devpocket.sh"

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
