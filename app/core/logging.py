import logging
import sys
from typing import Any, Dict

import structlog

from app.core.config import settings


def configure_logging():
    """Configure structured logging for the application"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer()
            if settings.LOG_FORMAT == "json"
            else structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper())
        ),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )

    return structlog.get_logger()


class LoggingMixin:
    """Mixin to add structured logging to classes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = structlog.get_logger(self.__class__.__name__)


def log_request_response(func):
    """Decorator to log API requests and responses"""

    async def wrapper(*args, **kwargs):
        logger = structlog.get_logger()

        try:
            # Log request
            logger.info(
                "API request started",
                endpoint=func.__name__,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )

            result = await func(*args, **kwargs)

            # Log successful response
            logger.info("API request completed successfully", endpoint=func.__name__)

            return result

        except Exception as e:
            # Log error
            logger.error(
                "API request failed",
                endpoint=func.__name__,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    return wrapper


def audit_log(action: str, user_id: str = None, details: Dict[str, Any] = None):
    """Create audit log entry"""
    logger = structlog.get_logger("audit")

    log_data = {
        "action": action,
        "timestamp": structlog.processors.TimeStamper(fmt="iso"),
    }

    if user_id:
        log_data["user_id"] = user_id

    if details:
        log_data.update(details)

    logger.info("Audit log entry", **log_data)
