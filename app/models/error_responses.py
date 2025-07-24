"""
Common error response schemas for OpenAPI documentation.

This module defines reusable error response schemas that can be imported
and used across all API endpoints to ensure consistent error documentation.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error detail structure"""
    detail: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Error description"
            }
        }


class ValidationErrorDetail(BaseModel):
    """Validation error detail with field information"""
    detail: str
    errors: Optional[List[Dict[str, Any]]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Validation error",
                "errors": [
                    {
                        "loc": ["body", "email"],
                        "msg": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        }


# Common error responses for reuse across endpoints
COMMON_ERROR_RESPONSES = {
    400: {
        "description": "Bad Request - Invalid request data",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Invalid request data or parameters"
                }
            }
        }
    },
    401: {
        "description": "Unauthorized - Invalid or missing authentication token",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Could not validate credentials"
                }
            }
        }
    },
    403: {
        "description": "Forbidden - Insufficient permissions or email not verified",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "email_not_verified": {
                        "summary": "Email not verified",
                        "value": {
                            "detail": "Please verify your email address"
                        }
                    },
                    "insufficient_permissions": {
                        "summary": "Insufficient permissions",
                        "value": {
                            "detail": "Not enough permissions"
                        }
                    },
                    "admin_required": {
                        "summary": "Admin access required",
                        "value": {
                            "detail": "Admin access required"
                        }
                    }
                }
            }
        }
    },
    404: {
        "description": "Not Found - Resource does not exist",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "user_not_found": {
                        "summary": "User not found",
                        "value": {
                            "detail": "User not found"
                        }
                    },
                    "environment_not_found": {
                        "summary": "Environment not found",
                        "value": {
                            "detail": "Environment not found"
                        }
                    },
                    "template_not_found": {
                        "summary": "Template not found",
                        "value": {
                            "detail": "Template not found"
                        }
                    },
                    "cluster_not_found": {
                        "summary": "Cluster not found",
                        "value": {
                            "detail": "Cluster not found"
                        }
                    }
                }
            }
        }
    },
    409: {
        "description": "Conflict - Resource already exists or operation conflicts with current state",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "email_exists": {
                        "summary": "Email already registered",
                        "value": {
                            "detail": "Email already registered"
                        }
                    },
                    "username_exists": {
                        "summary": "Username already taken",
                        "value": {
                            "detail": "Username already taken"
                        }
                    },
                    "environment_name_exists": {
                        "summary": "Environment name already exists",
                        "value": {
                            "detail": "Environment with this name already exists"
                        }
                    }
                }
            }
        }
    },
    422: {
        "description": "Unprocessable Entity - Validation error",
        "model": ValidationErrorDetail,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Validation error",
                    "errors": [
                        {
                            "loc": ["body", "email"],
                            "msg": "field required",
                            "type": "value_error.missing"
                        },
                        {
                            "loc": ["body", "password"],
                            "msg": "ensure this value has at least 8 characters",
                            "type": "value_error.any_str.min_length",
                            "ctx": {"limit_value": 8}
                        }
                    ]
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests - Rate limit exceeded",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Rate limit exceeded. Please try again later."
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error - An unexpected error occurred",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "examples": {
                    "generic_error": {
                        "summary": "Generic server error",
                        "value": {
                            "detail": "Internal server error"
                        }
                    },
                    "database_error": {
                        "summary": "Database error",
                        "value": {
                            "detail": "Database connection failed"
                        }
                    },
                    "external_service_error": {
                        "summary": "External service error",
                        "value": {
                            "detail": "External service unavailable"
                        }
                    }
                }
            }
        }
    },
    503: {
        "description": "Service Unavailable - Service is temporarily unavailable",
        "model": ErrorDetail,
        "content": {
            "application/json": {
                "example": {
                    "detail": "Service temporarily unavailable"
                }
            }
        }
    }
}


def get_error_responses(*error_codes: int) -> Dict[int, Dict]:
    """
    Get specific error responses for endpoint documentation.
    
    Args:
        *error_codes: HTTP status codes to include
        
    Returns:
        Dictionary of error responses for the specified codes
        
    Example:
        responses=get_error_responses(400, 401, 404, 500)
    """
    return {code: COMMON_ERROR_RESPONSES[code] for code in error_codes if code in COMMON_ERROR_RESPONSES}


def get_auth_error_responses() -> Dict[int, Dict]:
    """Get common authentication-related error responses (401, 403)"""
    return get_error_responses(401, 403)


def get_crud_error_responses() -> Dict[int, Dict]:
    """Get common CRUD operation error responses (400, 401, 403, 404, 500)"""
    return get_error_responses(400, 401, 403, 404, 500)


def get_admin_error_responses() -> Dict[int, Dict]:
    """Get common admin operation error responses (401, 403, 500)"""
    return get_error_responses(401, 403, 500)


def get_validation_error_responses() -> Dict[int, Dict]:
    """Get validation error responses (400, 422)"""
    return get_error_responses(400, 422)