from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import structlog

from app.core.database import get_database
from app.services.environment_service import environment_service
from app.models.environment import (
    EnvironmentCreate, EnvironmentResponse, EnvironmentStatus,
    EnvironmentUpdate, EnvironmentMetrics
)
from app.models.user import UserInDB
from app.middleware.auth import get_current_user, get_current_verified_user
from app.core.logging import audit_log

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/", response_model=EnvironmentResponse, status_code=status.HTTP_201_CREATED)
async def create_environment(
    env_data: EnvironmentCreate,
    current_user: UserInDB = Depends(get_current_verified_user),
    db=Depends(get_database)
):
    """Create a new development environment"""
    try:
        environment_service.set_database(db)
        
        # Create environment
        environment = await environment_service.create_environment(current_user, env_data)
        
        # Audit log
        audit_log(
            action="environment_created",
            user_id=str(current_user.id),
            details={
                "environment_id": str(environment.id),
                "name": environment.name,
                "template": environment.template.value
            }
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
            storage_usage=environment.storage_usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create environment"
        )

@router.get("/", response_model=List[EnvironmentResponse])
async def list_environments(
    current_user: UserInDB = Depends(get_current_user),
    status_filter: Optional[EnvironmentStatus] = Query(None, description="Filter by status"),
    db=Depends(get_database)
):
    """List all environments for current user"""
    try:
        environment_service.set_database(db)
        
        # Get user environments
        environments = await environment_service.get_user_environments(str(current_user.id))
        
        # Filter by status if provided
        if status_filter:
            environments = [env for env in environments if env.status == status_filter]
        
        # Convert to response models
        response = []
        for env in environments:
            response.append(EnvironmentResponse(
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
                storage_usage=env.storage_usage
            ))
        
        return response
        
    except Exception as e:
        logger.error(f"Environment listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve environments"
        )

@router.get("/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get specific environment details"""
    try:
        environment_service.set_database(db)
        
        # Get environment
        environment = await environment_service.get_environment(environment_id, str(current_user.id))
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found"
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
            storage_usage=environment.storage_usage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve environment"
        )

@router.delete("/{environment_id}")
async def delete_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """Delete an environment"""
    try:
        environment_service.set_database(db)
        
        # Delete environment
        success = await environment_service.delete_environment(environment_id, str(current_user.id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found"
            )
        
        # Audit log
        audit_log(
            action="environment_deleted",
            user_id=str(current_user.id),
            details={"environment_id": environment_id}
        )
        
        return {"message": "Environment deletion started"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete environment"
        )

@router.post("/{environment_id}/start")
async def start_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """Start a stopped environment"""
    try:
        environment_service.set_database(db)
        
        # Start environment
        success = await environment_service.start_environment(environment_id, str(current_user.id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found or cannot be started"
            )
        
        # Audit log
        audit_log(
            action="environment_started",
            user_id=str(current_user.id),
            details={"environment_id": environment_id}
        )
        
        return {"message": "Environment started successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment start error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not start environment"
        )

@router.post("/{environment_id}/stop")
async def stop_environment(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """Stop a running environment"""
    try:
        environment_service.set_database(db)
        
        # Stop environment
        success = await environment_service.stop_environment(environment_id, str(current_user.id))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found or cannot be stopped"
            )
        
        # Audit log
        audit_log(
            action="environment_stopped",
            user_id=str(current_user.id),
            details={"environment_id": environment_id}
        )
        
        return {"message": "Environment stopped successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Environment stop error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not stop environment"
        )

@router.get("/{environment_id}/metrics")
async def get_environment_metrics(
    environment_id: str,
    current_user: UserInDB = Depends(get_current_user),
    hours: int = Query(24, description="Number of hours of metrics to retrieve", ge=1, le=168),
    db=Depends(get_database)
):
    """Get environment metrics"""
    try:
        # Check if user owns the environment
        environment_service.set_database(db)
        environment = await environment_service.get_environment(environment_id, str(current_user.id))
        if not environment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environment not found"
            )
        
        # Get metrics from database (last N hours)
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(hours=hours)
        
        cursor = db.environment_metrics.find({
            "environment_id": environment_id,
            "timestamp": {"$gte": since}
        }).sort("timestamp", 1)
        
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
            detail="Could not retrieve metrics"
        )