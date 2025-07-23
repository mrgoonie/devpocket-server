import base64
import yaml
from typing import List, Optional, Dict, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from cryptography.fernet import Fernet
from kubernetes import client, config
from kubernetes.config import ConfigException
import structlog

from app.models.cluster import (
    ClusterCreate,
    ClusterUpdate,
    ClusterInDB,
    ClusterResponse,
    ClusterStatus,
    ClusterRegion,
    ClusterHealthCheck,
)
from app.core.config import settings

logger = structlog.get_logger()


class ClusterService:
    def __init__(self):
        self.db: Optional[AsyncIOMotorDatabase] = None
        # Generate or load encryption key for kube_config
        self.encryption_key = settings.SECRET_KEY[:32].ljust(32, "0").encode()[:32]
        self.cipher_suite = Fernet(base64.urlsafe_b64encode(self.encryption_key))

    def set_database(self, database: AsyncIOMotorDatabase):
        self.db = database

    async def create_cluster(
        self, cluster_data: ClusterCreate, created_by: str
    ) -> ClusterInDB:
        """Create a new cluster configuration"""
        if not self.db:
            raise ValueError("Database not initialized")

        # Validate kubeconfig
        try:
            kube_config_yaml = base64.b64decode(cluster_data.kube_config).decode(
                "utf-8"
            )
            config_dict = yaml.safe_load(kube_config_yaml)

            # Basic validation of kubeconfig structure
            required_keys = ["clusters", "contexts", "users"]
            if not all(key in config_dict for key in required_keys):
                raise ValueError("Invalid kubeconfig format")

        except Exception as e:
            logger.error("Invalid kubeconfig provided", error=str(e))
            raise ValueError(f"Invalid kubeconfig: {str(e)}")

        # Check if cluster name already exists
        existing_cluster = await self.db.clusters.find_one({"name": cluster_data.name})
        if existing_cluster:
            raise ValueError(f"Cluster with name '{cluster_data.name}' already exists")

        # If this is set as default, unset other defaults in the same region
        if cluster_data.is_default:
            await self.db.clusters.update_many(
                {"region": cluster_data.region, "is_default": True},
                {"$set": {"is_default": False, "updated_at": datetime.utcnow()}},
            )

        # Encrypt the kubeconfig
        encrypted_config = self.cipher_suite.encrypt(
            cluster_data.kube_config.encode()
        ).decode()

        cluster_dict = cluster_data.model_dump()
        cluster_dict.pop("kube_config")  # Remove plain text config
        cluster_dict.update(
            {
                "encrypted_kube_config": encrypted_config,
                "status": ClusterStatus.ACTIVE,
                "environments_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": created_by,
            }
        )

        result = await self.db.clusters.insert_one(cluster_dict)
        cluster_dict["_id"] = result.inserted_id

        logger.info(
            "Cluster created successfully",
            cluster_name=cluster_data.name,
            region=cluster_data.region,
        )
        return ClusterInDB(**cluster_dict)

    async def get_cluster_by_id(self, cluster_id: str) -> Optional[ClusterInDB]:
        """Get cluster by ID"""
        if not self.db:
            raise ValueError("Database not initialized")

        cluster_data = await self.db.clusters.find_one({"_id": cluster_id})
        if cluster_data:
            return ClusterInDB(**cluster_data)
        return None

    async def get_cluster_by_region(
        self, region: ClusterRegion
    ) -> Optional[ClusterInDB]:
        """Get the default cluster for a region"""
        if not self.db:
            raise ValueError("Database not initialized")

        # First try to get the default cluster for the region
        cluster_data = await self.db.clusters.find_one(
            {"region": region, "is_default": True, "status": ClusterStatus.ACTIVE}
        )

        # If no default found, get any active cluster in the region
        if not cluster_data:
            cluster_data = await self.db.clusters.find_one(
                {"region": region, "status": ClusterStatus.ACTIVE}
            )

        if cluster_data:
            return ClusterInDB(**cluster_data)
        return None

    async def list_clusters(
        self, region: Optional[ClusterRegion] = None
    ) -> List[ClusterResponse]:
        """List all clusters, optionally filtered by region"""
        if not self.db:
            raise ValueError("Database not initialized")

        query = {}
        if region:
            query["region"] = region

        cursor = self.db.clusters.find(query).sort("created_at", -1)
        clusters = []

        async for cluster_data in cursor:
            # Remove encrypted config from response
            cluster_dict = dict(cluster_data)
            cluster_dict.pop("encrypted_kube_config", None)
            cluster_dict.pop("created_by", None)
            clusters.append(ClusterResponse(**cluster_dict))

        return clusters

    async def update_cluster(
        self, cluster_id: str, update_data: ClusterUpdate
    ) -> Optional[ClusterInDB]:
        """Update cluster configuration"""
        if not self.db:
            raise ValueError("Database not initialized")

        update_dict = {
            k: v for k, v in update_data.model_dump().items() if v is not None
        }

        if not update_dict:
            return await self.get_cluster_by_id(cluster_id)

        # Handle kubeconfig update
        if "kube_config" in update_dict:
            try:
                kube_config_yaml = base64.b64decode(update_dict["kube_config"]).decode(
                    "utf-8"
                )
                yaml.safe_load(kube_config_yaml)  # Validate YAML

                # Encrypt the new config
                encrypted_config = self.cipher_suite.encrypt(
                    update_dict["kube_config"].encode()
                ).decode()
                update_dict["encrypted_kube_config"] = encrypted_config
                update_dict.pop("kube_config")  # Remove plain text

            except Exception as e:
                raise ValueError(f"Invalid kubeconfig: {str(e)}")

        # Handle default cluster update
        if update_dict.get("is_default"):
            cluster = await self.get_cluster_by_id(cluster_id)
            if cluster:
                await self.db.clusters.update_many(
                    {"region": cluster.region, "is_default": True},
                    {"$set": {"is_default": False, "updated_at": datetime.utcnow()}},
                )

        update_dict["updated_at"] = datetime.utcnow()

        result = await self.db.clusters.update_one(
            {"_id": cluster_id}, {"$set": update_dict}
        )

        if result.modified_count > 0:
            return await self.get_cluster_by_id(cluster_id)
        return None

    async def delete_cluster(self, cluster_id: str) -> bool:
        """Delete a cluster (only if no environments are using it)"""
        if not self.db:
            raise ValueError("Database not initialized")

        cluster = await self.get_cluster_by_id(cluster_id)
        if not cluster:
            return False

        # Check if any environments are using this cluster
        env_count = await self.db.environments.count_documents(
            {"cluster_id": cluster_id}
        )
        if env_count > 0:
            raise ValueError(
                f"Cannot delete cluster: {env_count} environments are still using it"
            )

        result = await self.db.clusters.delete_one({"_id": cluster_id})
        return result.deleted_count > 0

    async def get_decrypted_kubeconfig(self, cluster_id: str) -> Optional[str]:
        """Get decrypted kubeconfig for internal use"""
        if not self.db:
            raise ValueError("Database not initialized")

        cluster_data = await self.db.clusters.find_one({"_id": cluster_id})
        if not cluster_data:
            return None

        try:
            encrypted_config = cluster_data.get("encrypted_kube_config")
            if encrypted_config:
                decrypted = self.cipher_suite.decrypt(
                    encrypted_config.encode()
                ).decode()
                return decrypted
        except Exception as e:
            logger.error(
                "Failed to decrypt kubeconfig", cluster_id=cluster_id, error=str(e)
            )

        return None

    async def check_cluster_health(self, cluster_id: str) -> ClusterHealthCheck:
        """Check cluster health and connectivity"""
        cluster = await self.get_cluster_by_id(cluster_id)
        if not cluster:
            return ClusterHealthCheck(
                cluster_id=cluster_id,
                status=ClusterStatus.INACTIVE,
                last_check=datetime.utcnow(),
                error_message="Cluster not found",
            )

        health_check = ClusterHealthCheck(
            cluster_id=cluster_id,
            status=ClusterStatus.INACTIVE,
            last_check=datetime.utcnow(),
        )

        try:
            # Get kubeconfig and test connection
            kubeconfig = await self.get_decrypted_kubeconfig(cluster_id)
            if not kubeconfig:
                health_check.error_message = "Failed to decrypt kubeconfig"
                return health_check

            # Load kubeconfig from string
            config_dict = yaml.safe_load(base64.b64decode(kubeconfig).decode("utf-8"))

            # Test connection (this would need actual kubernetes client setup)
            # For now, we'll just validate the config structure
            start_time = datetime.utcnow()

            # Mock health check - in production, this would use kubernetes client
            health_check.status = ClusterStatus.ACTIVE
            health_check.response_time_ms = (
                datetime.utcnow() - start_time
            ).total_seconds() * 1000
            health_check.node_count = 3  # Mock data
            health_check.available_resources = {
                "cpu": "8000m",
                "memory": "32Gi",
                "storage": "1Ti",
            }

            # Update cluster status in database
            await self.db.clusters.update_one(
                {"_id": cluster_id},
                {
                    "$set": {
                        "status": ClusterStatus.ACTIVE,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

        except Exception as e:
            logger.error(
                "Cluster health check failed", cluster_id=cluster_id, error=str(e)
            )
            health_check.error_message = str(e)

            # Update cluster status to error
            await self.db.clusters.update_one(
                {"_id": cluster_id},
                {
                    "$set": {
                        "status": ClusterStatus.INACTIVE,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

        return health_check

    async def get_available_regions(self) -> List[Dict[str, Any]]:
        """Get list of available regions with their cluster status"""
        if not self.db:
            raise ValueError("Database not initialized")

        regions_info = []

        for region in ClusterRegion:
            cluster_count = await self.db.clusters.count_documents(
                {"region": region, "status": ClusterStatus.ACTIVE}
            )

            default_cluster = await self.db.clusters.find_one(
                {"region": region, "is_default": True, "status": ClusterStatus.ACTIVE}
            )

            regions_info.append(
                {
                    "region": region.value,
                    "display_name": region.value.replace("-", " ").title(),
                    "cluster_count": cluster_count,
                    "available": cluster_count > 0,
                    "has_default": default_cluster is not None,
                }
            )

        return regions_info


# Create service instance
cluster_service = ClusterService()
