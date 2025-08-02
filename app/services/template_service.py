from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog
from bson import ObjectId

from app.constants import SYSTEM_USER_ID
from app.models.template import (
    TemplateCategory,
    TemplateCreate,
    TemplateInDB,
    TemplateResponse,
    TemplateStatus,
    TemplateUpdate,
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
                "name": "coding-agent",
                "display_name": "Coding Agent (Ubuntu + AI Tools)",
                "description": "Ubuntu environment with AI coding tools pre-installed including Claude Code, Gemini CLI, Qwen Code and Open Code. Perfect for AI-assisted development with sudo access.",
                "category": TemplateCategory.PROGRAMMING_LANGUAGE,
                "tags": [
                    "ubuntu",
                    "linux",
                    "ai",
                    "claude-code",
                    "gemini",
                    "qwen",
                    "coding-assistant",
                    "development",
                    "sudo",
                ],
                "docker_image": "ubuntu:22.04",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "1000m",
                    "memory": "2Gi",
                    "storage": "20Gi",
                },
                "environment_variables": {
                    "DEBIAN_FRONTEND": "noninteractive",
                    "TERM": "xterm-256color",
                    "USER": "devpocket",
                    "HOME": "/home/devpocket",
                    "PATH": "/home/devpocket/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                },
                "startup_commands": [
                    "apt-get update",
                    "apt-get install -y sudo curl wget git vim nano build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release python3 python3-pip nodejs npm",
                    "useradd -m -s /bin/bash devpocket",
                    "echo 'devpocket:devpocket' | chpasswd",
                    "usermod -aG sudo devpocket",
                    "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                    "mkdir -p /home/devpocket/workspace /home/devpocket/.local/bin",
                    "chown -R devpocket:devpocket /home/devpocket",
                    # Install Claude Code
                    "su - devpocket -c 'curl -fsSL https://claude.ai/cli/install.sh | bash'",
                    # Install Python tools
                    "su - devpocket -c 'pip3 install --user qwencoder-cli'",
                    # Install VS Code
                    "wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg",
                    "install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/",
                    "echo 'deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main' > /etc/apt/sources.list.d/vscode.list",
                    "apt-get update",
                    "apt-get install -y code",
                    # Add useful aliases with simpler syntax
                    "su - devpocket -c 'echo \"alias ll=ls -la\" >> ~/.bashrc'",
                    "su - devpocket -c 'echo \"cd ~/workspace\" >> ~/.bashrc'",
                    "su - devpocket -c 'echo \"alias claude=claude-code\" >> ~/.bashrc'",
                ],
                "documentation_url": "https://claude.ai/code",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-plain.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "ubuntu",
                "display_name": "Ubuntu 22.04 LTS",
                "description": "Ubuntu environment with sudo access and essential development tools. Includes a non-root user with sudo privileges for package installation and system management.",
                "category": TemplateCategory.OPERATING_SYSTEM,
                "tags": ["ubuntu", "linux", "bash", "shell", "development", "sudo"],
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
                    "USER": "devpocket",
                    "HOME": "/home/devpocket",
                },
                "startup_commands": [
                    "apt-get update",
                    "apt-get install -y sudo curl wget git vim nano build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release unzip tar gzip",
                    "useradd -m -s /bin/bash devpocket",
                    "echo 'devpocket:devpocket' | chpasswd",
                    "usermod -aG sudo devpocket",
                    "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                    "mkdir -p /home/devpocket/workspace",
                    "chown -R devpocket:devpocket /home/devpocket",
                    "su - devpocket -c 'echo \"alias ll=ls -la\" >> ~/.bashrc'",
                    "su - devpocket -c 'echo \"cd ~/workspace\" >> ~/.bashrc'",
                ],
                "documentation_url": "https://ubuntu.com/server/docs",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/ubuntu/ubuntu-plain.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "centos",
                "display_name": "CentOS Stream 9",
                "description": "CentOS environment with sudo access and essential development tools. Includes a non-root user with sudo privileges for package installation and system management.",
                "category": TemplateCategory.OPERATING_SYSTEM,
                "tags": [
                    "centos",
                    "linux",
                    "bash",
                    "shell",
                    "development",
                    "sudo",
                    "redhat",
                ],
                "docker_image": "quay.io/centos/centos:stream9",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "500m",
                    "memory": "1Gi",
                    "storage": "10Gi",
                },
                "environment_variables": {
                    "TERM": "xterm-256color",
                    "USER": "devpocket",
                    "HOME": "/home/devpocket",
                },
                "startup_commands": [
                    "dnf update -y",
                    "dnf groupinstall -y 'Development Tools'",
                    "dnf install -y sudo curl wget git vim nano unzip tar gzip which",
                    "useradd -m -s /bin/bash devpocket",
                    "echo 'devpocket:devpocket' | chpasswd",
                    "usermod -aG wheel devpocket",
                    "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                    "mkdir -p /home/devpocket/workspace",
                    "chown -R devpocket:devpocket /home/devpocket",
                    "su - devpocket -c 'echo \"alias ll=ls -la\" >> ~/.bashrc'",
                    "su - devpocket -c 'echo \"cd ~/workspace\" >> ~/.bashrc'",
                ],
                "documentation_url": "https://docs.centos.org/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/centos/centos-original.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "debian",
                "display_name": "Debian 12 (Bookworm)",
                "description": "Debian environment with sudo access and essential development tools. Includes a non-root user with sudo privileges for package installation and system management.",
                "category": TemplateCategory.OPERATING_SYSTEM,
                "tags": ["debian", "linux", "bash", "shell", "development", "sudo"],
                "docker_image": "debian:12",
                "default_port": 8080,
                "default_resources": {
                    "cpu": "500m",
                    "memory": "1Gi",
                    "storage": "10Gi",
                },
                "environment_variables": {
                    "DEBIAN_FRONTEND": "noninteractive",
                    "TERM": "xterm-256color",
                    "USER": "devpocket",
                    "HOME": "/home/devpocket",
                },
                "startup_commands": [
                    "apt-get update",
                    "apt-get install -y sudo curl wget git vim nano build-essential software-properties-common apt-transport-https ca-certificates gnupg unzip tar gzip",
                    "useradd -m -s /bin/bash devpocket",
                    "echo 'devpocket:devpocket' | chpasswd",
                    "usermod -aG sudo devpocket",
                    "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                    "mkdir -p /home/devpocket/workspace",
                    "chown -R devpocket:devpocket /home/devpocket",
                    "su - devpocket -c 'echo \"alias ll=ls -la\" >> ~/.bashrc'",
                    "su - devpocket -c 'echo \"cd ~/workspace\" >> ~/.bashrc'",
                ],
                "documentation_url": "https://www.debian.org/doc/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/debian/debian-original.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "nodejs",
                "display_name": "Node.js 18 LTS",
                "description": "Node.js development environment with npm, yarn, and popular packages. Includes sudo access for system package installation and essential development tools.",
                "category": TemplateCategory.PROGRAMMING_LANGUAGE,
                "tags": [
                    "nodejs",
                    "npm",
                    "yarn",
                    "express",
                    "react",
                    "vue",
                    "javascript",
                    "sudo",
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
                    "DEBIAN_FRONTEND": "noninteractive",
                    "USER": "devpocket",
                    "HOME": "/home/devpocket",
                },
                "startup_commands": [
                    "apt-get update",
                    "apt-get install -y sudo curl wget git vim nano build-essential unzip tar gzip",
                    "useradd -m -s /bin/bash devpocket",
                    "echo 'devpocket:devpocket' | chpasswd",
                    "usermod -aG sudo devpocket",
                    "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                    "mkdir -p /home/devpocket/workspace",
                    "chown -R devpocket:devpocket /home/devpocket",
                    "su - devpocket -c 'npm install -g nodemon typescript @types/node yarn'",
                    "su - devpocket -c 'echo \"alias ll=ls -la\" >> ~/.bashrc'",
                    "su - devpocket -c 'echo \"cd ~/workspace\" >> ~/.bashrc'",
                ],
                "documentation_url": "https://nodejs.org/en/docs/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nodejs/nodejs-original.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
            {
                "name": "python",
                "display_name": "Python 3.11",
                "description": "Python development environment with pip, virtualenv, and common packages pre-installed. Includes sudo access for system package installation and essential development tools.",
                "category": TemplateCategory.PROGRAMMING_LANGUAGE,
                "tags": [
                    "python",
                    "python3",
                    "pip",
                    "virtualenv",
                    "flask",
                    "django",
                    "sudo",
                ],
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
                    "DEBIAN_FRONTEND": "noninteractive",
                    "USER": "devpocket",
                    "HOME": "/home/devpocket",
                },
                "startup_commands": [
                    "apt-get update",
                    "apt-get install -y sudo curl wget git vim nano build-essential unzip tar gzip",
                    "useradd -m -s /bin/bash devpocket",
                    "echo 'devpocket:devpocket' | chpasswd",
                    "usermod -aG sudo devpocket",
                    "echo 'devpocket ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
                    "mkdir -p /home/devpocket/workspace",
                    "chown -R devpocket:devpocket /home/devpocket",
                    "su - devpocket -c 'pip install --upgrade pip'",
                    "su - devpocket -c 'pip install flask fastapi uvicorn jupyter pandas numpy requests virtualenv'",
                    "su - devpocket -c 'echo \"alias ll=ls -la\" >> ~/.bashrc'",
                    "su - devpocket -c 'echo \"cd ~/workspace\" >> ~/.bashrc'",
                ],
                "documentation_url": "https://docs.python.org/3/",
                "icon_url": "https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg",
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
            },
        ]

        for template_data in default_templates:
            template_data.update(
                {
                    "status": TemplateStatus.ACTIVE,
                    "version": "1.0.0",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "created_by": SYSTEM_USER_ID,
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

        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(template_id)
        except Exception:
            # Invalid ObjectId format
            return None

        template_data = await self.db.templates.find_one({"_id": object_id})
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
        self, template_data: TemplateCreate, created_by: str = None
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
        template_dict = (
            template_data.dict()
            if hasattr(template_data, "dict")
            else template_data.model_dump()
        )
        template_dict.update(
            {
                "status": TemplateStatus.ACTIVE,
                "version": "1.0.0",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "created_by": ObjectId(created_by) if created_by else SYSTEM_USER_ID,
                "usage_count": 0,
            }
        )

        result = await self.db.templates.insert_one(template_dict)
        template_dict["_id"] = str(result.inserted_id)

        logger.info(f"Template created: {template_data.name}")
        return TemplateInDB(**template_dict)

    async def create_template_from_data(self, template_data: dict) -> TemplateInDB:
        """Create a template from raw dictionary data (e.g., from YAML file)"""
        try:
            # Convert dictionary to TemplateInDB object
            template = TemplateInDB(
                _id=ObjectId(),
                name=template_data["name"],
                display_name=template_data["display_name"],
                description=template_data["description"],
                category=TemplateCategory(template_data["category"]),
                tags=template_data.get("tags", []),
                docker_image=template_data["docker_image"],
                default_port=template_data.get("default_port", 8080),
                default_resources=template_data.get("default_resources", {}),
                environment_variables=template_data.get("environment_variables", {}),
                startup_commands=template_data.get("startup_commands", []),
                documentation_url=template_data.get("documentation_url"),
                icon_url=template_data.get("icon_url"),
                usage_count=0,
                is_active=True,
                created_by=ObjectId(SYSTEM_USER_ID),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Insert into database
            result = await self.db.templates.insert_one(
                template.model_dump(by_alias=True)
            )
            template.id = str(result.inserted_id)

            logger.info(f"Created template from data: {template.name}")
            return template

        except Exception as e:
            logger.error(f"Error creating template from data: {e}")
            raise

    async def update_template(
        self, template_id: str, update_data: TemplateUpdate
    ) -> Optional[TemplateInDB]:
        """Update template"""
        if self.db is None:
            raise ValueError("Database not initialized")

        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(template_id)
        except Exception:
            # Invalid ObjectId format
            return None

        update_dict = {
            k: v
            for k, v in (
                update_data.dict()
                if hasattr(update_data, "dict")
                else update_data.model_dump()
            ).items()
            if v is not None
        }

        if not update_dict:
            return await self.get_template_by_id(template_id)

        update_dict["updated_at"] = datetime.now(timezone.utc)

        result = await self.db.templates.update_one(
            {"_id": object_id}, {"$set": update_dict}
        )

        if result.modified_count > 0:
            return await self.get_template_by_id(template_id)
        return None

    async def delete_template(self, template_id: str) -> bool:
        """Delete template (set status to deprecated instead of actual deletion)"""
        if self.db is None:
            raise ValueError("Database not initialized")

        try:
            # Convert string ID to ObjectId for MongoDB query
            object_id = ObjectId(template_id)
        except Exception:
            # Invalid ObjectId format
            return False

        result = await self.db.templates.update_one(
            {"_id": object_id},
            {
                "$set": {
                    "status": TemplateStatus.DEPRECATED,
                    "updated_at": datetime.now(timezone.utc),
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
            {
                "$inc": {"usage_count": 1},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
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

    async def validate_template_packages(self, template_data: dict) -> dict:
        """Validate packages in template startup commands to prevent 404 errors"""
        import asyncio
        import re
        from typing import Union

        import httpx

        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "validated_packages": [],
        }

        # Safely extract startup_commands with type checking
        startup_commands_raw = template_data.get("startup_commands", [])

        # Ensure startup_commands is a list of strings
        startup_commands = []
        if isinstance(startup_commands_raw, list):
            for cmd in startup_commands_raw:
                if isinstance(cmd, str):
                    startup_commands.append(cmd)
                elif isinstance(cmd, dict):
                    # Handle case where command might be a dict with a 'command' field
                    if "command" in cmd:
                        startup_commands.append(str(cmd["command"]))
                    else:
                        logger.warning(f"Unexpected command format in template: {cmd}")
                        validation_results["warnings"].append(
                            f"Skipped non-string command: {type(cmd).__name__}"
                        )
                else:
                    # Convert other types to string
                    startup_commands.append(str(cmd))
                    validation_results["warnings"].append(
                        f"Converted {type(cmd).__name__} command to string"
                    )
        else:
            logger.error(
                f"startup_commands is not a list: {type(startup_commands_raw)}"
            )
            validation_results["errors"].append(
                f"Invalid startup_commands format: expected list, got {type(startup_commands_raw).__name__}"
            )
            return validation_results

        async def validate_npm_package(
            package_name: str,
        ) -> Dict[str, Union[bool, str]]:
            """Validate npm package availability"""
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Use npm registry API to check package
                    url = f"https://registry.npmjs.org/{package_name}"
                    response = await client.get(url)

                    if response.status_code == 200:
                        return {"valid": True, "package": package_name, "type": "npm"}
                    elif response.status_code == 404:
                        return {
                            "valid": False,
                            "package": package_name,
                            "type": "npm",
                            "error": "Package not found",
                        }
                    else:
                        return {
                            "valid": False,
                            "package": package_name,
                            "type": "npm",
                            "error": f"HTTP {response.status_code}",
                        }
            except Exception as e:
                return {
                    "valid": False,
                    "package": package_name,
                    "type": "npm",
                    "error": str(e),
                }

        async def validate_pip_package(
            package_name: str,
        ) -> Dict[str, Union[bool, str]]:
            """Validate pip package availability"""
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Use PyPI API to check package
                    url = f"https://pypi.org/pypi/{package_name}/json"
                    response = await client.get(url)

                    if response.status_code == 200:
                        return {"valid": True, "package": package_name, "type": "pip"}
                    elif response.status_code == 404:
                        return {
                            "valid": False,
                            "package": package_name,
                            "type": "pip",
                            "error": "Package not found",
                        }
                    else:
                        return {
                            "valid": False,
                            "package": package_name,
                            "type": "pip",
                            "error": f"HTTP {response.status_code}",
                        }
            except Exception as e:
                return {
                    "valid": False,
                    "package": package_name,
                    "type": "pip",
                    "error": str(e),
                }

        # Extract package names from commands
        npm_packages = []
        pip_packages = []

        for cmd in startup_commands:
            try:
                # Ensure cmd is a string
                cmd_str = str(cmd)

                # Extract npm packages - improved regex pattern
                npm_pattern = r"npm\s+install\s+(?:-g\s+)?(?:--global\s+)?((?:[^\s'\"]+(?:\s+[^\s'\"]+)*)*)"
                npm_matches = re.findall(npm_pattern, cmd_str)
                for match in npm_matches:
                    # Split multiple packages and filter out flags
                    packages = match.split()
                    for package in packages:
                        package = package.strip("'\" ")
                        if (
                            package
                            and not package.startswith("-")
                            and package not in ["install", "-g", "--global", "npm"]
                        ):
                            npm_packages.append(package)

                # Extract pip packages - improved regex pattern
                pip_pattern = r"pip(?:[0-9])?(?:\.exe)?\s+install\s+(?:--[^\s]+\s+)*((?:[^\s'\"]+(?:\s+[^\s'\"]+)*)*)"
                pip_matches = re.findall(pip_pattern, cmd_str)
                for match in pip_matches:
                    # Split multiple packages and filter out flags
                    packages = match.split()
                    for package in packages:
                        package = package.strip("'\" ")
                        if (
                            package
                            and not package.startswith("-")
                            and package
                            not in ["install", "upgrade", "user", "pip", "pip3"]
                        ):
                            pip_packages.append(package)

            except Exception as e:
                logger.warning(f"Error parsing command '{cmd}': {e}")
                validation_results["warnings"].append(
                    f"Error parsing command: {str(e)}"
                )
                continue

        # Remove duplicates while preserving order
        npm_packages = list(dict.fromkeys(npm_packages))
        pip_packages = list(dict.fromkeys(pip_packages))

        logger.info(f"Extracted packages - NPM: {npm_packages}, PIP: {pip_packages}")

        # Validate packages concurrently
        validation_tasks = []

        for package in npm_packages:
            validation_tasks.append(validate_npm_package(package))

        for package in pip_packages:
            validation_tasks.append(validate_pip_package(package))

        if validation_tasks:
            try:
                results = await asyncio.gather(
                    *validation_tasks, return_exceptions=True
                )

                for result in results:
                    if isinstance(result, Exception):
                        validation_results["warnings"].append(
                            f"Validation error: {str(result)}"
                        )
                        continue

                    validation_results["validated_packages"].append(result)

                    if not result["valid"]:
                        validation_results["valid"] = False
                        error_msg = f"{result['type'].upper()} package '{result['package']}': {result['error']}"
                        validation_results["errors"].append(error_msg)
                        logger.warning(f"Template validation failed: {error_msg}")

            except Exception as e:
                logger.error(f"Error during package validation: {e}")
                validation_results["warnings"].append(
                    f"Validation process error: {str(e)}"
                )

        return validation_results

    async def get_validated_default_templates(self) -> List[dict]:
        """Get default templates with package validation"""
        templates = await self.get_default_templates()
        validated_templates = []

        for template in templates:
            logger.info(f"Validating template: {template['name']}")
            validation_result = await self.validate_template_packages(template)

            # Add validation metadata to template
            template["validation"] = {
                "validated_at": datetime.now(timezone.utc),
                "is_valid": validation_result["valid"],
                "warnings": validation_result["warnings"],
                "errors": validation_result["errors"],
                "validated_packages": validation_result["validated_packages"],
            }

            # Filter out invalid packages from startup_commands if needed
            if not validation_result["valid"]:
                logger.warning(
                    f"Template '{template['name']}' has package validation issues"
                )
                template["status"] = (
                    TemplateStatus.INACTIVE
                    if len(validation_result["errors"]) > 2
                    else TemplateStatus.ACTIVE
                )

                # Optionally remove commands with invalid packages
                filtered_commands = []
                for cmd in template["startup_commands"]:
                    should_include = True
                    for error in validation_result["errors"]:
                        if "not found" in error and any(
                            pkg in cmd for pkg in [error.split("'")[1]] if "'" in error
                        ):
                            should_include = False
                            logger.info(f"Removing problematic command: {cmd}")
                            break
                    if should_include:
                        filtered_commands.append(cmd)

                template["startup_commands"] = filtered_commands

            validated_templates.append(template)

        return validated_templates


# Global instance
template_service = TemplateService()
