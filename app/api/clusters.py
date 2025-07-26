from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.middleware.auth import get_current_active_user, require_admin
from app.models.cluster import (
    ClusterCreate,
    ClusterHealthCheck,
    ClusterRegion,
    ClusterResponse,
    ClusterUpdate,
)
from app.models.user import UserInDB
from app.services.cluster_service import cluster_service

logger = structlog.get_logger()

router = APIRouter()


@router.post("", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
async def create_cluster(
    cluster_data: ClusterCreate,
    current_user: UserInDB = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Create a new cluster configuration (Admin only)"""
    try:
        cluster_service.set_database(db)
        cluster = await cluster_service.create_cluster(
            cluster_data, str(current_user.id)
        )

        # Convert to response model (excluding sensitive data)
        cluster_dict = cluster.model_dump()
        cluster_dict.pop("encrypted_kube_config", None)
        cluster_dict.pop("created_by", None)

        logger.info(
            "Cluster created",
            cluster_name=cluster.name,
            created_by=current_user.username,
        )
        return ClusterResponse(**cluster_dict)

    except ValueError as e:
        logger.warning(
            "Cluster creation failed", error=str(e), created_by=current_user.username
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Unexpected error creating cluster",
            error=str(e),
            created_by=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create cluster",
        )


@router.get("", response_model=List[ClusterResponse])
async def list_clusters(
    region: Optional[ClusterRegion] = Query(None, description="Filter by region"),
    current_user: UserInDB = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """List all clusters (Admin only)"""
    try:
        cluster_service.set_database(db)
        clusters = await cluster_service.list_clusters(region=region)

        logger.info(
            "Clusters listed", count=len(clusters), requested_by=current_user.username
        )
        return clusters

    except Exception as e:
        logger.error(
            "Failed to list clusters", error=str(e), requested_by=current_user.username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list clusters",
        )


@router.get("/regions")
async def get_available_regions(
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get list of available regions for environment creation"""
    try:
        cluster_service.set_database(db)
        regions = await cluster_service.get_available_regions()

        # Filter to only show regions with available clusters
        available_regions = [r for r in regions if r["available"]]

        logger.info(
            "Available regions requested",
            count=len(available_regions),
            requested_by=current_user.username,
        )
        return {"regions": available_regions}

    except Exception as e:
        logger.error(
            "Failed to get available regions",
            error=str(e),
            requested_by=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get regions",
        )


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: str,
    current_user: UserInDB = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Get cluster details by ID (Admin only)"""
    try:
        cluster_service.set_database(db)
        cluster = await cluster_service.get_cluster_by_id(cluster_id)

        if not cluster:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
            )

        # Convert to response model (excluding sensitive data)
        cluster_dict = cluster.model_dump()
        cluster_dict.pop("encrypted_kube_config", None)
        cluster_dict.pop("created_by", None)

        logger.info(
            "Cluster details requested",
            cluster_id=cluster_id,
            requested_by=current_user.username,
        )
        return ClusterResponse(**cluster_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get cluster",
            cluster_id=cluster_id,
            error=str(e),
            requested_by=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cluster",
        )


@router.put("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: str,
    update_data: ClusterUpdate,
    current_user: UserInDB = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Update cluster configuration (Admin only)"""
    try:
        cluster_service.set_database(db)
        cluster = await cluster_service.update_cluster(cluster_id, update_data)

        if not cluster:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
            )

        # Convert to response model (excluding sensitive data)
        cluster_dict = cluster.model_dump()
        cluster_dict.pop("encrypted_kube_config", None)
        cluster_dict.pop("created_by", None)

        logger.info(
            "Cluster updated", cluster_id=cluster_id, updated_by=current_user.username
        )
        return ClusterResponse(**cluster_dict)

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "Cluster update failed",
            cluster_id=cluster_id,
            error=str(e),
            updated_by=current_user.username,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to update cluster",
            cluster_id=cluster_id,
            error=str(e),
            updated_by=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cluster",
        )


@router.delete("/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cluster(
    cluster_id: str,
    current_user: UserInDB = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Delete a cluster (Admin only)"""
    try:
        cluster_service.set_database(db)
        deleted = await cluster_service.delete_cluster(cluster_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found"
            )

        logger.info(
            "Cluster deleted", cluster_id=cluster_id, deleted_by=current_user.username
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(
            "Cluster deletion failed",
            cluster_id=cluster_id,
            error=str(e),
            deleted_by=current_user.username,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(
            "Failed to delete cluster",
            cluster_id=cluster_id,
            error=str(e),
            deleted_by=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cluster",
        )


@router.get("/{cluster_id}/health", response_model=ClusterHealthCheck)
async def check_cluster_health(
    cluster_id: str,
    current_user: UserInDB = Depends(require_admin),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Check cluster health and connectivity (Admin only)"""
    try:
        cluster_service.set_database(db)
        health_check = await cluster_service.check_cluster_health(cluster_id)

        logger.info(
            "Cluster health checked",
            cluster_id=cluster_id,
            status=health_check.status,
            requested_by=current_user.username,
        )
        return health_check

    except Exception as e:
        logger.error(
            "Failed to check cluster health",
            cluster_id=cluster_id,
            error=str(e),
            requested_by=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check cluster health",
        )
