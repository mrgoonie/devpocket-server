from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from app.models.template import (
    TemplateCreate,
    TemplateInDB,
    TemplateResponse,
    TemplateUpdate,
    TemplateCategory,
    TemplateStatus,
)

logger = structlog.get_logger(__name__)


class TemplateService:
    """Service for managing environment templates"""

    def __init__(self):
        self.db = None

    def set_database(self, db):
        """Set database instance"""
        self.db = db

    async def get_default_templates(self) -> List[dict]:
        """Get list of default templates"""
        default_templates = [
            {
                "name": "python",
                "display_name": "Python 3.11",
                "description": "Python development environment with pip, virtualenv, and common packages pre-installed. Includes VS Code Server for web-based development.",
                "category": TemplateCategory.PROGRAMMING_LANGUAGE,
                "tags": ["python", "python3", "pip", "virtualenv", "flask", "django"],
                "docker_image": "python:3.11-slim",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "500m",
                    "memory": "1Gi",
                    "storage": "10Gi",
                },
                "environment_variables": {
                    "PYTHONPATH": "/workspace",
                    "PIP_CACHE_DIR": "/tmp/pip-cache",
                },
                "startup_commands": [
                    "pip install --upgrade pip",
                    "pip install flask fastapi uvicorn jupyter",
                    "mkdir -p /workspace",
                ],
                "documentation_url": "https://docs.python.org/3/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "nodejs",
                "display_name": "Node.js 18 LTS",
                "description": "Node.js development environment with npm, yarn, and popular packages. Perfect for building web applications, APIs, and microservices.",
                "category": TemplateCategory.PROGRAMMING_LANGUAGE,
                "tags": [
                    "nodejs",
                    "npm",
                    "yarn",
                    "express",
                    "react",
                    "vue",
                    "javascript",
                ],
                "docker_image": "node:18-slim",
                "default_port": 3000,
                "default_resources": {
                    "cpu": "500m",
                    "memory": "1Gi",
                    "storage": "10Gi",
                },
                "environment_variables": {
                    "NODE_ENV": "development",
                    "npm_config_cache": "/tmp/npm-cache",
                },
                "startup_commands": [
                    "npm install -g nodemon typescript @types/node",
                    "mkdir -p /workspace",
                    "cd /workspace",
                ],
                "documentation_url": "https://nodejs.org/en/docs/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "golang",
                "display_name": "Go 1.21",
                "description": "Go development environment with the latest Go compiler and common tools. Ideal for building fast, reliable, and efficient software.",
                "category": TemplateCategory.PROGRAMMING_LANGUAGE,
                "tags": ["go", "golang", "gin", "fiber", "gorilla"],
                "docker_image": "golang:1.21-alpine",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "500m",
                    "memory": "1Gi",
                    "storage": "10Gi",
                },
                "environment_variables": {
                    "GOPATH": "/go",
                    "GOROOT": "/usr/local/go",
                    "PATH": "/usr/local/go/bin:/go/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                },
                "startup_commands": [
                    "go install github.com/air-verse/air@latest",
                    "go install github.com/cosmtrek/air@latest",
                    "mkdir -p /workspace",
                ],
                "documentation_url": "https://golang.org/doc/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/go/go-original.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "rust",
                "display_name": "Rust Latest",
                "description": "Rust development environment with rustc, cargo, and essential tools. Build fast and memory-safe applications.",
                "category": TemplateCategory.PROGRAMMING_LANGUAGE,
                "tags": ["rust", "cargo", "rustc", "actix", "tokio"],
                "docker_image": "rust:latest",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "1000m",
                    "memory": "2Gi",
                    "storage": "15Gi",
                },
                "environment_variables": {
                    "CARGO_HOME": "/usr/local/cargo",
                    "RUSTUP_HOME": "/usr/local/rustup",
                },
                "startup_commands": [
                    "rustup update",
                    "cargo install cargo-watch",
                    "mkdir -p /workspace",
                ],
                "documentation_url": "https://doc.rust-lang.org/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/rust/rust-plain.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "ubuntu",
                "display_name": "Ubuntu 22.04 LTS",
                "description": "Clean Ubuntu environment with essential development tools. Perfect for custom setups and system administration tasks.",
                "category": TemplateCategory.OPERATING_SYSTEM,
                "tags": ["ubuntu", "linux", "bash", "shell", "development"],
                "docker_image": "ubuntu:22.04",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "500m",
                    "memory": "1Gi",
                    "storage": "10Gi",
                },
                "environment_variables": {
                    "DEBIAN_FRONTEND": "noninteractive",
                    "TERM": "xterm-256color",
                },
                "startup_commands": [
                    "apt-get update",
                    "apt-get install -y curl wget git vim nano build-essential",
                    "mkdir -p /workspace",
                ],
                "documentation_url": "https://ubuntu.com/server/docs",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-plain.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
        ]

        for template_data in default_templates:
            template_data.update(
                {
                    "status": TemplateStatus.ACTIVE,
                    "version": "1.0.0",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "created_by": "system",
                    "usage_count": 0,
                }
            )

        return default_templates

    async def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        status: Optional[TemplateStatus] = None,
    ) -> List[TemplateResponse]:
        """List available templates"""
        if self.db is None:
            raise ValueError("Database not initialized")

        # Build query
        query = {}
        if category:
            query["category"] = category
        if status:
            query["status"] = status

        logger.info(
            f"Building database query for templates",
            query=query,
            category=category.value if category else None,
            status=status.value if status else None,
        )

        # Check if we have templates in database
        count = await self.db.templates.count_documents({})
        logger.info(f"Total templates in database: {count}")

        if count == 0:
            # Initialize default templates
            await self.initialize_default_templates()
            # Re-count after initialization
            count = await self.db.templates.count_documents({})
            logger.info(f"Templates after initialization: {count}")

        # Get templates from database
        cursor = self.db.templates.find(query).sort("created_at", 1)
        templates = []

        logger.info(f"Executing database query for templates", query=query)

        template_count = 0
        async for template_data in cursor:
            template_count += 1
            logger.info(
                f"Processing template #{template_count}",
                template_name=template_data.get("name", "unknown"),
                template_id=str(template_data.get("_id", "unknown")),
                template_status=template_data.get("status", "unknown"),
            )
            try:
                template_dict = dict(template_data)
                template_dict["id"] = str(template_dict.pop("_id"))

                logger.info(
                    f"Converting template to response format",
                    template_name=template_dict.get("name", "unknown"),
                    template_keys=list(template_dict.keys()),
                )

                template_response = TemplateResponse(**template_dict)
                templates.append(template_response)

                logger.info(
                    f"Successfully converted template",
                    template_name=template_dict.get("name", "unknown"),
                )

            except Exception as e:
                logger.error(
                    f"Error converting template to response",
                    template_name=template_data.get("name", "unknown"),
                    template_id=str(template_data.get("_id", "unknown")),
                    error=str(e),
                    template_data=template_data,
                    error_type=type(e).__name__,
                )
                # Continue processing other templates instead of failing completely

        logger.info(
            f"Successfully converted {len(templates)} templates out of {count} total"
        )
        return templates

    async def get_template_by_id(self, template_id: str) -> Optional[TemplateInDB]:
        """Get template by ID"""
        if self.db is None:
            raise ValueError("Database not initialized")

        template_data = await self.db.templates.find_one({"_id": template_id})
        if template_data:
            template_data["_id"] = str(template_data["_id"])
            return TemplateInDB(**template_data)
        return None

    async def get_template_by_name(self, name: str) -> Optional[TemplateInDB]:
        """Get template by name"""
        if self.db is None:
            raise ValueError("Database not initialized")

        template_data = await self.db.templates.find_one({"name": name})
        if template_data:
            template_data["_id"] = str(template_data["_id"])
            return TemplateInDB(**template_data)
        return None

    async def create_template(
        self, template_data: TemplateCreate, created_by: str = "system"
    ) -> TemplateInDB:
        """Create a new template"""
        if self.db is None:
            raise ValueError("Database not initialized")

        # Check if template name already exists
        existing = await self.get_template_by_name(template_data.name)
        if existing:
            raise ValueError(
                f"Template with name '{template_data.name}' already exists"
            )

        # Create template document
        template_dict = template_data.model_dump()
        template_dict.update(
            {
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": created_by,
                "usage_count": 0,
            }
        )

        result = await self.db.templates.insert_one(template_dict)
        template_dict["_id"] = str(result.inserted_id)

        logger.info(f"Template created: {template_data.name}")
        return TemplateInDB(**template_dict)

    async def update_template(
        self, template_id: str, update_data: TemplateUpdate
    ) -> Optional[TemplateInDB]:
        """Update template"""
        if self.db is None:
            raise ValueError("Database not initialized")

        update_dict = {
            k: v for k, v in update_data.model_dump().items() if v is not None
        }

        if not update_dict:
            return await self.get_template_by_id(template_id)

        update_dict["updated_at"] = datetime.utcnow()

        result = await self.db.templates.update_one(
            {"_id": template_id}, {"$set": update_dict}
        )

        if result.modified_count > 0:
            return await self.get_template_by_id(template_id)
        return None

    async def delete_template(self, template_id: str) -> bool:
        """Delete template (set status to deprecated instead of actual deletion)"""
        if self.db is None:
            raise ValueError("Database not initialized")

        result = await self.db.templates.update_one(
            {"_id": template_id},
            {
                "$set": {
                    "status": TemplateStatus.DEPRECATED,
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return result.modified_count > 0

    async def increment_usage_count(self, template_id: str):
        """Increment template usage count"""
        if self.db is None:
            raise ValueError("Database not initialized")

        await self.db.templates.update_one(
            {"_id": template_id},
            {"$inc": {"usage_count": 1}, "$set": {"updated_at": datetime.utcnow()}},
        )

    async def initialize_default_templates(self):
        """Initialize default templates in database"""
        if self.db is None:
            raise ValueError("Database not initialized")

        default_templates = await self.get_default_templates()

        for template_dict in default_templates:
            # Check if template already exists
            existing = await self.get_template_by_name(template_dict["name"])
            if not existing:
                await self.db.templates.insert_one(template_dict)
                logger.info(f"Initialized default template: {template_dict['name']}")


# Global instance
template_service = TemplateService()
