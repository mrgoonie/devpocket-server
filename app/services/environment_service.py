import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
import structlog

from app.core.config import settings
from app.models.environment import (
    EnvironmentCreate,
    EnvironmentInDB,
    EnvironmentStatus,
    EnvironmentTemplate,
    ResourceLimits,
    WebSocketSession,
    EnvironmentMetrics,
)
from app.models.user import UserInDB

logger = structlog.get_logger(__name__)


class EnvironmentService:
    """Service for managing development environments (containers/pods)"""

    def __init__(self):
        self.db = None
        self.active_sessions: Dict[str, WebSocketSession] = {}

    def set_database(self, db):
        """Set database instance"""
        self.db = db

    async def create_environment(
        self, user: UserInDB, env_data: EnvironmentCreate
    ) -> EnvironmentInDB:
        """Create a new development environment"""
        try:
            # Check user's subscription limits
            await self._check_user_limits(user)

            # Set default resources based on subscription
            resources = env_data.resources or self._get_default_resources(user)

            # Generate unique names
            namespace = f"user-{str(user.id)}"
            pod_name = f"{env_data.name}-{uuid.uuid4().hex[:8]}"
            service_name = f"svc-{pod_name}"

            # Create environment document
            environment = EnvironmentInDB(
                user_id=str(user.id),
                name=env_data.name,
                template=env_data.template,
                status=EnvironmentStatus.CREATING,
                resources=resources,
                environment_variables=env_data.environment_variables or {},
                namespace=namespace,
                pod_name=pod_name,
                service_name=service_name,
            )

            # Save to database
            env_dict = environment.dict(by_alias=True)
            env_dict.pop("id", None)  # Remove id for insert

            result = await self.db.environments.insert_one(env_dict)
            environment.id = result.inserted_id

            # Create the actual container/pod (async)
            asyncio.create_task(self._create_container(environment))

            logger.info(
                f"Environment creation started: {env_data.name} for user {user.username}"
            )
            return environment

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating environment: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create environment",
            )

    async def _check_user_limits(self, user: UserInDB):
        """Check if user can create more environments"""
        # Count user's active environments
        active_count = await self.db.environments.count_documents(
            {"user_id": str(user.id), "status": {"$in": ["creating", "running"]}}
        )

        # Set limits based on subscription
        limits = {"free": 1, "starter": 3, "pro": 10, "admin": 100}

        max_environments = limits.get(user.subscription_plan, 1)

        if active_count >= max_environments:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Environment limit reached. Upgrade your plan to create more environments.",
            )

    def _get_default_resources(self, user: UserInDB) -> ResourceLimits:
        """Get default resource limits based on user subscription"""
        resource_presets = {
            "free": ResourceLimits(cpu="500m", memory="1Gi", storage="5Gi"),
            "starter": ResourceLimits(cpu="1000m", memory="2Gi", storage="10Gi"),
            "pro": ResourceLimits(cpu="2000m", memory="4Gi", storage="20Gi"),
            "admin": ResourceLimits(cpu="4000m", memory="8Gi", storage="50Gi"),
        }

        return resource_presets.get(user.subscription_plan, resource_presets["free"])

    async def _create_container(self, environment: EnvironmentInDB):
        """Create the actual container/pod (simulated)"""
        try:
            # Update status to creating
            await self.db.environments.update_one(
                {"_id": environment.id},
                {"$set": {"status": EnvironmentStatus.CREATING.value}},
            )

            # Simulate container creation process
            await asyncio.sleep(10)  # Simulated creation time

            # In a real implementation, this would:
            # 1. Create Kubernetes namespace
            # 2. Create persistent volume claim
            # 3. Create deployment with appropriate image
            # 4. Create service for networking
            # 5. Set up ingress for external access

            # For now, simulate success
            external_url = f"https://env-{environment.pod_name}.devpocket.io"
            web_port = 8080
            ssh_port = 2222

            # Update environment with created resources
            await self.db.environments.update_one(
                {"_id": environment.id},
                {
                    "$set": {
                        "status": EnvironmentStatus.RUNNING.value,
                        "external_url": external_url,
                        "web_port": web_port,
                        "ssh_port": ssh_port,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            logger.info(f"Environment created successfully: {environment.name}")

        except Exception as e:
            logger.error(
                f"Error creating container for environment {environment.id}: {e}"
            )

            # Update status to error
            await self.db.environments.update_one(
                {"_id": environment.id},
                {
                    "$set": {
                        "status": EnvironmentStatus.ERROR.value,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

    async def get_user_environments(self, user_id: str) -> List[EnvironmentInDB]:
        """Get all environments for a user"""
        try:
            cursor = self.db.environments.find({"user_id": user_id})
            environments = []

            async for env_doc in cursor:
                environments.append(EnvironmentInDB(**env_doc))

            return environments

        except Exception as e:
            logger.error(f"Error getting user environments: {e}")
            return []

    async def get_environment(
        self, env_id: str, user_id: str
    ) -> Optional[EnvironmentInDB]:
        """Get specific environment for user"""
        try:
            env_doc = await self.db.environments.find_one(
                {"_id": env_id, "user_id": user_id}
            )

            if env_doc:
                return EnvironmentInDB(**env_doc)
            return None

        except Exception as e:
            logger.error(f"Error getting environment: {e}")
            return None

    async def delete_environment(self, env_id: str, user_id: str) -> bool:
        """Delete an environment"""
        try:
            # Get environment first
            environment = await self.get_environment(env_id, user_id)
            if not environment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Environment not found",
                )

            # Update status to terminating
            await self.db.environments.update_one(
                {"_id": env_id},
                {"$set": {"status": EnvironmentStatus.TERMINATED.value}},
            )

            # Delete the actual container/pod (async)
            asyncio.create_task(self._delete_container(environment))

            logger.info(f"Environment deletion started: {environment.name}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting environment: {e}")
            return False

    async def _delete_container(self, environment: EnvironmentInDB):
        """Delete the actual container/pod (simulated)"""
        try:
            # Simulate deletion time
            await asyncio.sleep(5)

            # In a real implementation, this would:
            # 1. Delete Kubernetes deployment
            # 2. Delete service
            # 3. Delete persistent volume claim
            # 4. Clean up namespace if empty

            # Remove from database
            await self.db.environments.delete_one({"_id": environment.id})

            logger.info(f"Environment deleted successfully: {environment.name}")

        except Exception as e:
            logger.error(
                f"Error deleting container for environment {environment.id}: {e}"
            )

    async def start_environment(self, env_id: str, user_id: str) -> bool:
        """Start a stopped environment"""
        try:
            environment = await self.get_environment(env_id, user_id)
            if not environment:
                return False

            if environment.status != EnvironmentStatus.STOPPED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Environment is not in stopped state",
                )

            # Update status
            await self.db.environments.update_one(
                {"_id": env_id}, {"$set": {"status": EnvironmentStatus.RUNNING.value}}
            )

            logger.info(f"Environment started: {environment.name}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error starting environment: {e}")
            return False

    async def stop_environment(self, env_id: str, user_id: str) -> bool:
        """Stop a running environment"""
        try:
            environment = await self.get_environment(env_id, user_id)
            if not environment:
                return False

            if environment.status != EnvironmentStatus.RUNNING:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Environment is not running",
                )

            # Update status
            await self.db.environments.update_one(
                {"_id": env_id}, {"$set": {"status": EnvironmentStatus.STOPPED.value}}
            )

            logger.info(f"Environment stopped: {environment.name}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error stopping environment: {e}")
            return False

    async def restart_environment(self, env_id: str, user_id: str) -> bool:
        """Restart an environment"""
        try:
            environment = await self.get_environment(env_id, user_id)
            if not environment:
                return False

            if environment.status not in [EnvironmentStatus.RUNNING, EnvironmentStatus.STOPPED, EnvironmentStatus.ERROR]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Environment cannot be restarted in current state",
                )

            # Update status to creating (restarting)
            await self.db.environments.update_one(
                {"_id": env_id}, 
                {
                    "$set": {
                        "status": EnvironmentStatus.CREATING.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Restart the container/pod (async)
            asyncio.create_task(self._restart_container(environment))

            logger.info(f"Environment restart initiated: {environment.name}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error restarting environment: {e}")
            return False

    async def _restart_container(self, environment: EnvironmentInDB):
        """Restart the actual container/pod (simulated)"""
        try:
            # Simulate restart time
            await asyncio.sleep(10)

            # In a real implementation, this would:
            # 1. Delete existing Kubernetes pod
            # 2. Wait for termination
            # 3. Create new pod with same configuration
            # 4. Wait for pod to be ready
            # 5. Update service endpoints if needed

            # Update status to running
            await self.db.environments.update_one(
                {"_id": environment.id},
                {
                    "$set": {
                        "status": EnvironmentStatus.RUNNING.value,
                        "updated_at": datetime.utcnow(),
                        "last_accessed": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Environment restarted successfully: {environment.name}")

        except Exception as e:
            logger.error(f"Error restarting container for environment {environment.id}: {e}")
            
            # Set status to error on restart failure
            await self.db.environments.update_one(
                {"_id": environment.id},
                {
                    "$set": {
                        "status": EnvironmentStatus.ERROR.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

    async def get_environment_logs(
        self, 
        env_id: str, 
        user_id: str, 
        lines: int = 100,
        since_timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get environment logs"""
        try:
            environment = await self.get_environment(env_id, user_id)
            if not environment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Environment not found",
                )

            # In a real implementation, this would:
            # 1. Connect to Kubernetes API
            # 2. Get pod logs using kubectl logs
            # 3. Parse and format logs
            # 4. Return structured log data

            # For now, simulate logs based on environment status
            from app.models.template import LogEntry
            logs = await self._generate_simulated_logs(environment, lines, since_timestamp)
            
            return {
                "environment_id": env_id,
                "environment_name": environment.name,
                "logs": [log.model_dump() for log in logs],
                "total_lines": len(logs),
                "has_more": len(logs) >= lines
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting environment logs: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve logs"
            )

    async def _generate_simulated_logs(
        self, 
        environment: EnvironmentInDB, 
        lines: int,
        since_timestamp: Optional[datetime] = None
    ) -> List:
        """Generate simulated logs for demonstration"""
        from app.models.template import LogEntry
        import random
        
        # Base timestamp
        base_time = since_timestamp or datetime.utcnow()
        
        logs = []
        
        # Add some realistic log entries based on template
        template_logs = {
            EnvironmentTemplate.PYTHON: [
                "Starting Python application server",
                "Installing dependencies from requirements.txt",
                "Flask application started on port 8080",
                "DEBUG: Application initialized successfully",
                "INFO: Listening for connections on 0.0.0.0:8080"
            ],
            EnvironmentTemplate.NODEJS: [
                "npm install completed successfully",
                "Starting Node.js application",
                "Express server started on port 3000",
                "INFO: Application ready to accept connections",
                "DEBUG: Environment variables loaded"
            ],
            EnvironmentTemplate.GOLANG: [
                "Building Go application",
                "go mod download completed",
                "Starting HTTP server on :8080",
                "INFO: Application compiled successfully",
                "DEBUG: Server listening on port 8080"
            ],
            EnvironmentTemplate.UBUNTU: [
                "Container started successfully",
                "Installing development tools",
                "apt-get update completed",
                "System ready for development",
                "INFO: Environment setup completed"
            ]
        }
        
        template_specific_logs = template_logs.get(environment.template, template_logs[EnvironmentTemplate.UBUNTU])
        
        # Add status-specific logs
        if environment.status == EnvironmentStatus.CREATING:
            template_specific_logs.extend([
                "Initializing environment...",
                "Setting up workspace",
                "Configuring environment variables"
            ])
        elif environment.status == EnvironmentStatus.RUNNING:
            template_specific_logs.extend([
                "Application is running normally",
                "Health check passed",
                "Ready to accept requests"
            ])
        elif environment.status == EnvironmentStatus.ERROR:
            template_specific_logs.extend([
                "ERROR: Application failed to start",
                "ERROR: Port binding failed",
                "ERROR: Check configuration and retry"
            ])
        
        # Generate log entries
        for i in range(min(lines, len(template_specific_logs))):
            timestamp = base_time.replace(second=base_time.second + i)
            level = random.choice(["INFO", "DEBUG", "WARNING", "ERROR"]) if i % 5 == 0 else "INFO"
            
            logs.append(LogEntry(
                timestamp=timestamp,
                level=level,
                message=template_specific_logs[i % len(template_specific_logs)],
                source="container"
            ))
        
        return logs[-lines:]  # Return last N lines

    async def create_websocket_session(
        self, user_id: str, env_id: str, connection_id: str
    ) -> WebSocketSession:
        """Create a new WebSocket session"""
        try:
            session = WebSocketSession(
                user_id=user_id, environment_id=env_id, connection_id=connection_id
            )

            # Save to database
            session_dict = session.dict(by_alias=True)
            session_dict.pop("id", None)

            result = await self.db.websocket_sessions.insert_one(session_dict)
            session.id = result.inserted_id

            # Store in memory for quick access
            self.active_sessions[connection_id] = session

            logger.info(f"WebSocket session created: {connection_id}")
            return session

        except Exception as e:
            logger.error(f"Error creating WebSocket session: {e}")
            raise

    async def remove_websocket_session(self, connection_id: str):
        """Remove a WebSocket session"""
        try:
            # Remove from memory
            if connection_id in self.active_sessions:
                del self.active_sessions[connection_id]

            # Remove from database
            await self.db.websocket_sessions.delete_one(
                {"connection_id": connection_id}
            )

            logger.info(f"WebSocket session removed: {connection_id}")

        except Exception as e:
            logger.error(f"Error removing WebSocket session: {e}")

    async def record_metrics(self, env_id: str, metrics: EnvironmentMetrics):
        """Record environment metrics"""
        try:
            metrics_dict = metrics.dict()
            await self.db.environment_metrics.insert_one(metrics_dict)

        except Exception as e:
            logger.error(f"Error recording metrics: {e}")


# Global environment service instance
environment_service = EnvironmentService()
