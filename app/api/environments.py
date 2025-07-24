from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from typing import List, Optional
import structlog

from app.core.database import get_database
from app.services.environment_service import environment_service
from app.models.environment import (
    EnvironmentCreate,
    EnvironmentResponse,
    EnvironmentStatus,
    EnvironmentUpdate,
    EnvironmentMetrics,
)
from app.models.user import UserInDB
from app.middleware.auth import get_current_user, get_current_verified_user
from app.core.logging import audit_log

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_environment(
    env_data: EnvironmentCreate,
    current_user: UserInDB = Depends(get_current_verified_user),
    db=Depends(get_database),
):
    """Create a new development environment"""
    try:
        environment_service.set_database(db)

        # Create environment
        environment = await environment_service.create_environment(
            current_user, env_data
        )

        # Audit log
        audit_log(
            action="environment_created",
            user_id=str(current_user.id),
            details={
                "environment_id": str(environment.id),
                "name": environment.name,
                "template": environment.template.value,
            },
        )

        # Return response
        return EnvironmentResponse(
            id=str(environment.id),
            name=environment.name,
            template=environment.template,
            status=environment.status,
            resources=environment.resources,
            external_url=environment.external_url,
            web_port=environment.web_port,
            created_at=environment.created_at,
            last_accessed=environment.last_accessed,
            cpu_usage=environment.cpu_usage,
            memory_usage=environment.memory_usage,
            storage_usage=environment.storage_usage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create environment",
        )


@router.get("/", response_model=List[EnvironmentResponse])
async def list_environments(
    current_user: UserInDB = Depends(get_current_user),
    status_filter: Optional[EnvironmentStatus] = Query(
        None, description="Filter by status"
    ),
    db=Depends(get_database),
):
    """List all environments for current user"""
    try:
        environment_service.set_database(db)

        # Get user environments
        environments = await environment_service.get_user_environments(
            str(current_user.id)
        )

        # Filter by status if provided
        if status_filter:
            environments = [env for env in environments if env.status == status_filter]

        # Convert to response models
        response = []
        for env in environments:
            response.append(
                EnvironmentResponse(
                    id=str(env.id),
                    name=env.name,
                    template=env.template,
                    status=env.status,
                    resources=env.resources,
                    external_url=env.external_url,
                    web_port=env.web_port,
                    created_at=env.created_at,
                    last_accessed=env.last_accessed,
                    cpu_usage=env.cpu_usage,
                    memory_usage=env.memory_usage,
                    storage_usage=env.storage_usage,
                )
            )

        return response

    except Exception as e:
        logger.error(f"Environment listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve environments",
        )


@router.get("/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    """Get specific environment details"""
    try:
        environment_service.set_database(db)

        # Get environment
        environment = await environment_service.get_environment(
            environment_id, str(current_user.id)
        )
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found"
            )

        return EnvironmentResponse(
            id=str(environment.id),
            name=environment.name,
            template=environment.template,
            status=environment.status,
            resources=environment.resources,
            external_url=environment.external_url,
            web_port=environment.web_port,
            created_at=environment.created_at,
            last_accessed=environment.last_accessed,
            cpu_usage=environment.cpu_usage,
            memory_usage=environment.memory_usage,
            storage_usage=environment.storage_usage,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve environment",
        )


@router.delete("/{environment_id}")
async def delete_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    """Delete an environment"""
    try:
        environment_service.set_database(db)

        # Delete environment
        success = await environment_service.delete_environment(
            environment_id, str(current_user.id)
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found"
            )

        # Audit log
        audit_log(
            action="environment_deleted",
            user_id=str(current_user.id),
            details={"environment_id": environment_id},
        )

        return {"message": "Environment deletion started"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete environment",
        )


@router.post("/{environment_id}/start")
async def start_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    """Start a stopped environment"""
    try:
        environment_service.set_database(db)

        # Start environment
        success = await environment_service.start_environment(
            environment_id, str(current_user.id)
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found or cannot be started",
            )

        # Audit log
        audit_log(
            action="environment_started",
            user_id=str(current_user.id),
            details={"environment_id": environment_id},
        )

        return {"message": "Environment started successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment start error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not start environment",
        )


@router.post("/{environment_id}/stop")
async def stop_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    """Stop a running environment"""
    try:
        environment_service.set_database(db)

        # Stop environment
        success = await environment_service.stop_environment(
            environment_id, str(current_user.id)
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found or cannot be stopped",
            )

        # Audit log
        audit_log(
            action="environment_stopped",
            user_id=str(current_user.id),
            details={"environment_id": environment_id},
        )

        return {"message": "Environment stopped successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment stop error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not stop environment",
        )


@router.get("/{environment_id}/metrics")
async def get_environment_metrics(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    hours: int = Query(
        24, description="Number of hours of metrics to retrieve", ge=1, le=168
    ),
    db=Depends(get_database),
):
    """Get environment metrics"""
    try:
        # Check if user owns the environment
        environment_service.set_database(db)
        environment = await environment_service.get_environment(
            environment_id, str(current_user.id)
        )
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Environment not found"
            )

        # Get metrics from database (last N hours)
        from datetime import datetime, timedelta

        since = datetime.utcnow() - timedelta(hours=hours)

        cursor = db.environment_metrics.find(
            {"environment_id": environment_id, "timestamp": {"$gte": since}}
        ).sort("timestamp", 1)

        metrics = []
        async for metric_doc in cursor:
            metrics.append(EnvironmentMetrics(**metric_doc))

        return {"environment_id": environment_id, "metrics": metrics}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Metrics retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve metrics",
        )


@router.post(
    "/{environment_id}/restart",
    summary="Restart an environment",
    description="Restart a development environment by recreating its container",
    responses={
        200: {
            "description": "Environment restart initiated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Environment restart initiated successfully"
                    }
                }
            }
        },
        400: {
            "description": "Bad request - Environment cannot be restarted",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Environment cannot be restarted in current state"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
        404: {"description": "Environment not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Environment Management"]
)
async def restart_environment(
    environment_id: str = Path(
        ..., 
        description="The environment ID to restart",
        example="507f1f77bcf86cd799439011"
    ),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Restart a development environment.
    
    **Process:**
    1. Environment status changes to 'creating' (restarting)
    2. Container/pod is recreated with same configuration
    3. Status returns to 'running' when ready
    
    **Requirements:**
    - Environment must be in 'running', 'stopped', or 'error' state
    - User must own the environment
    
    **Note:** Restart typically takes 10-30 seconds
    """
    try:
        environment_service.set_database(db)

        # Restart environment
        success = await environment_service.restart_environment(
            environment_id, str(current_user.id)
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found or cannot be restarted",
            )

        # Audit log
        audit_log(
            action="environment_restarted",
            user_id=str(current_user.id),
            details={"environment_id": environment_id},
        )

        return {"message": "Environment restart initiated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment restart error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not restart environment",
        )


@router.get(
    "/{environment_id}/logs",
    summary="Get environment logs",
    description="Retrieve logs from a development environment",
    responses={
        200: {
            "description": "Logs retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "environment_id": "507f1f77bcf86cd799439011",
                        "environment_name": "my-python-env",
                        "logs": [
                            {
                                "timestamp": "2024-01-01T12:00:00Z",
                                "level": "INFO",
                                "message": "Starting Python application server",
                                "source": "container"
                            },
                            {
                                "timestamp": "2024-01-01T12:00:01Z",
                                "level": "INFO",
                                "message": "Flask application started on port 8080",
                                "source": "container"
                            }
                        ],
                        "total_lines": 2,
                        "has_more": False
                    }
                }
            }
        },
        400: {
            "description": "Bad request - Invalid timestamp format",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid timestamp format. Use ISO format (e.g., 2024-01-01T12:00:00Z)"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
        404: {"description": "Environment not found"},
        500: {"description": "Internal server error"}
    },
    tags=["Environment Monitoring"]
)
async def get_environment_logs(
    environment_id: str = Path(
        ..., 
        description="The environment ID to get logs from",
        example="507f1f77bcf86cd799439011"
    ),
    current_user: UserInDB = Depends(get_current_user),
    lines: int = Query(
        100, 
        description="Number of log lines to retrieve",
        ge=1,
        le=1000,
        example=100
    ),
    since: Optional[str] = Query(
        None,
        description="Get logs since timestamp (ISO 8601 format)",
        example="2024-01-01T12:00:00Z"
    ),
    db=Depends(get_database),
):
    """
    Get logs from a development environment.
    
    **Features:**
    - Retrieve last N lines of logs (up to 1000)
    - Filter logs by timestamp
    - Logs include level (INFO, DEBUG, WARNING, ERROR)
    - Real-time log streaming available via WebSocket endpoint
    
    **Log Levels:**
    - `INFO`: General information messages
    - `DEBUG`: Detailed debugging information
    - `WARNING`: Warning messages
    - `ERROR`: Error messages
    
    **Note:** In production, logs are retrieved from Kubernetes pod logs
    """
    try:
        environment_service.set_database(db)

        # Parse since timestamp if provided
        since_timestamp = None
        if since:
            try:
                from datetime import datetime
                since_timestamp = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid timestamp format. Use ISO format (e.g., 2024-01-01T12:00:00Z)"
                )

        # Get logs
        logs_data = await environment_service.get_environment_logs(
            environment_id, 
            str(current_user.id),
            lines=lines,
            since_timestamp=since_timestamp
        )

        return logs_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment logs retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve environment logs",
        )
