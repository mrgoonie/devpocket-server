from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
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


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[TemplateCategory] = Query(None, description="Filter by template category"),
    status_filter: Optional[TemplateStatus] = Query(None, alias="status", description="Filter by template status"),
    db=Depends(get_database),
    current_user: UserInDB = Depends(get_current_user)
) -> List[TemplateResponse]:
    """Get all available environment templates"""
    # CRITICAL DEBUG: Check if endpoint is reached
    print(f"[CRITICAL DEBUG] Templates endpoint called!")
    logger.info(
        "=== TEMPLATES ENDPOINT CALLED ===",
        endpoint="/api/v1/templates",
        method="GET",
        user_id=str(current_user.id) if current_user else "No user",
        category=category,
        status_filter=status_filter
    )
    
    try:
        template_service.set_database(db)
        
        # Get templates
        logger.info(
            f"Fetching templates from service",
            category=category,
            status_filter=status_filter,
            user_id=str(current_user.id),
            user_subscription=current_user.subscription_plan
        )
        
        templates = await template_service.list_templates(
            category=category,
            status=status_filter
        )
        
        logger.info(
            f"Templates fetched from service - raw count",
            raw_count=len(templates),
            raw_template_names=[t.name for t in templates] if templates else [],
            raw_template_statuses=[t.status.value for t in templates] if templates else [],
            user_id=str(current_user.id)
        )
        
        # Filter out deprecated templates for non-admin users
        # All users can see active templates, only admins can see deprecated ones
        initial_count = len(templates)
        is_admin = current_user.subscription_plan == "admin"
        
        if not is_admin:
            templates = [t for t in templates if t.status != TemplateStatus.DEPRECATED]
            logger.info(
                f"Filtered deprecated templates for non-admin user",
                user_subscription=current_user.subscription_plan,
                is_admin=is_admin,
                initial_count=initial_count,
                filtered_count=len(templates),
                user_id=str(current_user.id)
            )
        else:
            logger.info(
                f"Admin user sees all templates including deprecated",
                user_subscription=current_user.subscription_plan,
                is_admin=is_admin,
                template_count=len(templates),
                user_id=str(current_user.id)
            )
        
        # Log detailed information about templates and filtering
        template_statuses = [t.status.value for t in templates]
        logger.info(
            f"Templates listed - detailed info",
            user_id=str(current_user.id),
            user_subscription=current_user.subscription_plan,
            final_count=len(templates),
            category=category,
            status_filter=status_filter,
            template_names=[t.name for t in templates],
            template_statuses=template_statuses
        )
        
        return templates
        
    except Exception as e:
        logger.error(f"Template listing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve templates"
        )


@router.get(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Get template by ID",
    description="Retrieve detailed information about a specific template",
    responses={
        200: {
            "description": "Template details retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "507f1f77bcf86cd799439011",
                        "name": "nodejs",
                        "display_name": "Node.js 18 LTS",
                        "description": "Node.js development environment with npm, yarn, and popular packages",
                        "category": "programming_language",
                        "tags": ["nodejs", "npm", "yarn", "express", "react"],
                        "docker_image": "node:18-slim",
                        "default_port": 3000,
                        "default_resources": {
                            "cpu": "500m",
                            "memory": "1Gi",
                            "storage": "10Gi"
                        },
                        "environment_variables": {
                            "NODE_ENV": "development"
                        },
                        "startup_commands": ["npm install -g nodemon typescript"],
                        "documentation_url": "https://nodejs.org/en/docs/",
                        "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg",
                        "status": "active",
                        "version": "1.0.0",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "usage_count": 123
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"}
    }
)
async def get_template(
    template_id: str = Path(..., description="The template ID", example="507f1f77bcf86cd799439011"),
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database)
):
    """
    Get detailed information about a specific template.
    
    **Notes:**
    - All users can access active and beta templates
    - Only admin users (pro/admin subscription) can access deprecated templates
    - Template ID is a 24-character MongoDB ObjectId
    """
    try:
        template_service.set_database(db)
        
        template = await template_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Check if user can access deprecated templates
        # All users can see active templates, only admins can see deprecated ones
        is_admin = current_user.subscription_plan in ["pro", "admin"]
        if (template.status == TemplateStatus.DEPRECATED and not is_admin):
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


@router.post(
    "",
    response_model=TemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new template",
    description="Create a new environment template (Admin only)",
    responses={
        201: {
            "description": "Template created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "507f1f77bcf86cd799439011",
                        "name": "ruby",
                        "display_name": "Ruby 3.2",
                        "description": "Ruby development environment with bundler and Rails support",
                        "category": "programming_language",
                        "tags": ["ruby", "rails", "bundler"],
                        "docker_image": "ruby:3.2-slim",
                        "default_port": 3000,
                        "default_resources": {
                            "cpu": "500m",
                            "memory": "1Gi",
                            "storage": "10Gi"
                        },
                        "environment_variables": {
                            "RAILS_ENV": "development"
                        },
                        "startup_commands": ["gem install bundler rails"],
                        "documentation_url": "https://www.ruby-lang.org/en/documentation/",
                        "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ruby/ruby-original.svg",
                        "status": "active",
                        "version": "1.0.0",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "usage_count": 0
                    }
                }
            }
        },
        400: {"description": "Bad request - Template name already exists"},
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Admin access required"},
        500: {"description": "Internal server error"}
    }
)
async def create_template(
    template_data: TemplateCreate,
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """
    Create a new environment template.
    
    **Requirements:**
    - Admin access required
    - Template name must be unique
    - Valid Docker image must be specified
    
    **Template Categories:**
    - `programming_language`: Python, Node.js, Go, etc.
    - `framework`: Django, React, Angular, etc.
    - `database`: PostgreSQL, MongoDB, Redis, etc.
    - `devops`: Docker, Kubernetes, CI/CD tools
    - `operating_system`: Ubuntu, Alpine, Debian, etc.
    """
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


@router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Update a template",
    description="Update an existing template (Admin only)",
    responses={
        200: {
            "description": "Template updated successfully"
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Admin access required"},
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"}
    }
)
async def update_template(
    template_id: str = Path(..., description="The template ID to update", example="507f1f77bcf86cd799439011"),
    template_data: TemplateUpdate = ...,
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """
    Update an existing template.
    
    **Requirements:**
    - Admin access required
    - Only provided fields will be updated
    - Cannot change template name once created
    """
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


@router.delete(
    "/{template_id}",
    summary="Delete a template",
    description="Delete a template by setting its status to deprecated (Admin only)",
    responses={
        200: {
            "description": "Template deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Template deleted successfully"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Admin access required"},
        404: {"description": "Template not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_template(
    template_id: str = Path(..., description="The template ID to delete", example="507f1f77bcf86cd799439011"),
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """
    Delete a template (soft delete).
    
    **Important:**
    - Templates are not physically deleted
    - Status is set to 'deprecated'
    - Deprecated templates are hidden from non-admin users
    - Existing environments using this template will continue to work
    """
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


@router.post(
    "/initialize",
    summary="Initialize default templates",
    description="Initialize the system with default templates (Admin only)",
    responses={
        200: {
            "description": "Default templates initialized successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Default templates initialized successfully"
                    }
                }
            }
        },
        401: {"description": "Unauthorized - Invalid or missing token"},
        403: {"description": "Forbidden - Admin access required"},
        500: {"description": "Internal server error"}
    }
)
async def initialize_default_templates(
    current_admin: UserInDB = Depends(get_current_admin_user),
    db=Depends(get_database)
):
    """
    Initialize the system with default templates.
    
    **Default Templates:**
    - Python 3.11 with Flask/Django support
    - Node.js 18 LTS with npm/yarn
    - Go 1.21 with development tools
    - Rust Latest with cargo
    - Ubuntu 22.04 LTS base environment
    
    **Note:** Existing templates with the same names will be skipped
    """
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