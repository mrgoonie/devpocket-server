from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import structlog

from app.core.database import get_database
from app.services.template_service import template_service
from app.models.template import (
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
    TemplateCategory,
    TemplateStatus
)
from app.models.user import UserInDB
from app.middleware.auth import get_current_user, get_current_admin_user

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[TemplateCategory] = Query(None, description="Filter by category"),
    status_filter: Optional[TemplateStatus] = Query(None, alias="status", description="Filter by status"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """List all available environment templates"""
    try:
        template_service.set_database(db)
        
        # Get templates
        templates = await template_service.list_templates(
            category=category,
            status=status_filter
        )
        
        # Filter out deprecated templates for non-admin users
        if current_user.subscription_plan != "admin":
            templates = [t for t in templates if t.status != TemplateStatus.DEPRECATED]
        
        logger.info(
            f"Templates listed",
            user_id=str(current_user.id),
            count=len(templates),
            category=category,
            status=status_filter
        )
        
        return templates
        
    except Exception as e:
        logger.error(f"Template listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve templates"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """Get specific template details"""
    try:
        template_service.set_database(db)
        
        template = await template_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check if user can access deprecated templates
        if (template.status == TemplateStatus.DEPRECATED and 
            current_user.subscription_plan != "admin"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            category=template.category,
            tags=template.tags,
            docker_image=template.docker_image,
            default_port=template.default_port,
            default_resources=template.default_resources,
            environment_variables=template.environment_variables,
            startup_commands=template.startup_commands,
            documentation_url=template.documentation_url,
            icon_url=template.icon_url,
            status=template.status,
            version=template.version,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Template retrieval error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve template"
        )


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: TemplateCreate,
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Create a new template (Admin only)"""
    try:
        template_service.set_database(db)
        
        template = await template_service.create_template(
            template_data, 
            created_by=str(current_admin.id)
        )
        
        logger.info(
            f"Template created",
            admin_id=str(current_admin.id),
            template_id=template.id,
            template_name=template.name
        )
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            category=template.category,
            tags=template.tags,
            docker_image=template.docker_image,
            default_port=template.default_port,
            default_resources=template.default_resources,
            environment_variables=template.environment_variables,
            startup_commands=template.startup_commands,
            documentation_url=template.documentation_url,
            icon_url=template.icon_url,
            status=template.status,
            version=template.version,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Template creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create template"
        )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    template_data: TemplateUpdate,
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Update a template (Admin only)"""
    try:
        template_service.set_database(db)
        
        template = await template_service.update_template(template_id, template_data)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        logger.info(
            f"Template updated",
            admin_id=str(current_admin.id),
            template_id=template_id
        )
        
        return TemplateResponse(
            id=template.id,
            name=template.name,
            display_name=template.display_name,
            description=template.description,
            category=template.category,
            tags=template.tags,
            docker_image=template.docker_image,
            default_port=template.default_port,
            default_resources=template.default_resources,
            environment_variables=template.environment_variables,
            startup_commands=template.startup_commands,
            documentation_url=template.documentation_url,
            icon_url=template.icon_url,
            status=template.status,
            version=template.version,
            created_at=template.created_at,
            updated_at=template.updated_at,
            usage_count=template.usage_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Template update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update template"
        )


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Delete a template (Admin only) - Sets status to deprecated"""
    try:
        template_service.set_database(db)
        
        success = await template_service.delete_template(template_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        logger.info(
            f"Template deleted",
            admin_id=str(current_admin.id),
            template_id=template_id
        )
        
        return {"message": "Template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Template deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete template"
        )


@router.post("/initialize")
async def initialize_default_templates(
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """Initialize default templates (Admin only)"""
    try:
        template_service.set_database(db)
        
        await template_service.initialize_default_templates()
        
        logger.info(
            f"Default templates initialized",
            admin_id=str(current_admin.id)
        )
        
        return {"message": "Default templates initialized successfully"}
        
    except Exception as e:
        logger.error(f"Template initialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not initialize templates"
        )