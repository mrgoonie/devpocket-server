"""Tests for cluster service."""
import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from app.models.cluster import (
    ClusterCreate,
    ClusterInDB,
    ClusterRegion,
    ClusterStatus,
    ClusterUpdate,
)
from app.services.cluster_service import ClusterService


class TestClusterService:
    """Test ClusterService class."""

    def test_cluster_service_init(self):
        """Test ClusterService initialization."""
        service = ClusterService()

        assert service.db is None
        assert service.encryption_key is not None
        assert service.cipher_suite is not None

    def test_set_database(self):
        """Test setting database instance."""
        service = ClusterService()
        mock_db = MagicMock()

        service.set_database(mock_db)
        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_create_cluster_success(self):
        """Test successful cluster creation."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        # Mock no existing cluster with same name
        mock_clusters_collection.find_one.return_value = None

        # Mock successful insert
        cluster_id = ObjectId("507f1f77bcf86cd799439011")
        mock_clusters_collection.insert_one.return_value = MagicMock(
            inserted_id=cluster_id
        )

        # Mock the created cluster document
        created_cluster_doc = {
            "_id": cluster_id,
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "description": "Test cluster",
            "encrypted_kube_config": "encrypted_config",
            "status": "active",
            "is_default": False,
            "created_by": "admin_id",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_clusters_collection.find_one.side_effect = [None, created_cluster_doc]

        # Create valid base64 encoded kube config
        kube_config_yaml = """
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://test-cluster.example.com
  name: test-cluster
contexts:
- context:
    cluster: test-cluster
    user: test-user
  name: test-context
current-context: test-context
users:
- name: test-user
  user:
    token: test-token
"""
        kube_config_b64 = base64.b64encode(kube_config_yaml.encode()).decode()

        cluster_data = ClusterCreate(
            name="test-cluster",
            provider="aws",
            region="us-west-2",
            description="Test cluster",
            kube_config=kube_config_b64,
            is_default=False,
        )

        result = await service.create_cluster(cluster_data, "admin_id")

        assert isinstance(result, ClusterInDB)
        assert result.name == "test-cluster"
        assert result.provider == "aws"
        mock_clusters_collection.insert_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_cluster_duplicate_name(self):
        """Test cluster creation with duplicate name."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        # Mock existing cluster with same name
        existing_cluster = {"name": "test-cluster"}
        mock_clusters_collection.find_one.return_value = existing_cluster

        kube_config_yaml = "apiVersion: v1\nkind: Config"
        kube_config_b64 = base64.b64encode(kube_config_yaml.encode()).decode()

        cluster_data = ClusterCreate(
            name="test-cluster",
            provider="aws",
            region="us-west-2",
            kube_config=kube_config_b64,
        )

        with pytest.raises(ValueError, match="already exists"):
            await service.create_cluster(cluster_data)

    @pytest.mark.asyncio
    async def test_create_cluster_no_database(self):
        """Test cluster creation without database initialized."""
        service = ClusterService()

        cluster_data = ClusterCreate(
            name="test-cluster",
            provider="aws",
            region="us-west-2",
            kube_config="invalid_config",
        )

        with pytest.raises(ValueError, match="Database not initialized"):
            await service.create_cluster(cluster_data)

    @pytest.mark.asyncio
    async def test_create_cluster_invalid_kube_config(self):
        """Test cluster creation with invalid kube config."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        mock_clusters_collection.find_one.return_value = None

        cluster_data = ClusterCreate(
            name="test-cluster",
            provider="aws",
            region="us-west-2",
            kube_config="invalid_base64_config",
        )

        with pytest.raises(ValueError, match="Invalid kubeconfig"):
            await service.create_cluster(cluster_data)

    @pytest.mark.asyncio
    async def test_list_clusters_success(self):
        """Test successful cluster listing."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        # Mock cluster documents
        cluster_docs = [
            {
                "_id": ObjectId("507f1f77bcf86cd799439011"),
                "name": "cluster1",
                "provider": "aws",
                "region": "us-west-2",
                "status": "active",
                "is_default": True,
                "created_at": datetime.now(timezone.utc),
            },
            {
                "_id": ObjectId("507f1f77bcf86cd799439012"),
                "name": "cluster2",
                "provider": "gcp",
                "region": "us-central1",
                "status": "active",
                "is_default": False,
                "created_at": datetime.now(timezone.utc),
            },
        ]

        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = cluster_docs
        mock_clusters_collection.find.return_value = mock_cursor

        result = await service.list_clusters()

        assert len(result) == 2
        assert all(isinstance(cluster, ClusterInDB) for cluster in result)
        assert result[0].name == "cluster1"
        assert result[1].name == "cluster2"

    @pytest.mark.asyncio
    async def test_list_clusters_with_filters(self):
        """Test cluster listing with filters."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = []
        mock_clusters_collection.find.return_value = mock_cursor

        await service.list_clusters(region="us-west-2", provider="aws")

        # Verify find was called with filters
        mock_clusters_collection.find.assert_called_once()
        call_args = mock_clusters_collection.find.call_args[0][0]
        assert "region" in call_args
        assert "provider" in call_args

    @pytest.mark.asyncio
    async def test_get_cluster_success(self):
        """Test successful cluster retrieval."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"
        cluster_doc = {
            "_id": ObjectId(cluster_id),
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "status": "active",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
        }
        mock_clusters_collection.find_one.return_value = cluster_doc

        result = await service.get_cluster(cluster_id)

        assert isinstance(result, ClusterInDB)
        assert result.name == "test-cluster"
        mock_clusters_collection.find_one.assert_called_once_with(
            {"_id": ObjectId(cluster_id)}
        )

    @pytest.mark.asyncio
    async def test_get_cluster_not_found(self):
        """Test cluster retrieval with non-existent ID."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439999"
        mock_clusters_collection.find_one.return_value = None

        result = await service.get_cluster(cluster_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_cluster_success(self):
        """Test successful cluster update."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"
        update_data = ClusterUpdate(
            description="Updated description", status=ClusterStatus.MAINTENANCE
        )

        # Mock successful update
        mock_clusters_collection.update_one.return_value = MagicMock(modified_count=1)

        # Mock updated cluster document
        updated_cluster_doc = {
            "_id": ObjectId(cluster_id),
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "description": "Updated description",
            "status": "maintenance",
            "is_default": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        mock_clusters_collection.find_one.return_value = updated_cluster_doc

        result = await service.update_cluster(cluster_id, update_data)

        assert isinstance(result, ClusterInDB)
        assert result.description == "Updated description"
        assert result.status == "maintenance"
        mock_clusters_collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_cluster_not_found(self):
        """Test updating non-existent cluster."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439999"
        update_data = ClusterUpdate(description="Updated")

        # Mock no documents modified
        mock_clusters_collection.update_one.return_value = MagicMock(modified_count=0)

        result = await service.update_cluster(cluster_id, update_data)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_cluster_success(self):
        """Test successful cluster deletion."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_environments_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        mock_db.environments = mock_environments_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"

        # Mock get_cluster_by_id to return a cluster
        with patch.object(service, "get_cluster_by_id") as mock_get_cluster:
            from app.models.cluster import ClusterInDB

            mock_cluster = ClusterInDB(
                id=cluster_id,
                name="test-cluster",
                provider="aws",
                region="us-west-2",
                endpoint="https://k8s.test.com",
                encrypted_kube_config="encrypted_config",
                created_by="507f1f77bcf86cd799439012",
            )
            mock_get_cluster.return_value = mock_cluster

            # Mock environment count check (no environments using this cluster)
            mock_environments_collection.count_documents.return_value = 0

            # Mock successful deletion
            mock_delete_result = MagicMock()
            mock_delete_result.deleted_count = 1
            mock_clusters_collection.delete_one.return_value = mock_delete_result

            result = await service.delete_cluster(cluster_id)
            assert result is True
            mock_get_cluster.assert_called_once_with(cluster_id)
            mock_environments_collection.count_documents.assert_called_once_with(
                {"cluster_id": cluster_id}
            )
            mock_clusters_collection.delete_one.assert_called_once_with(
                {"_id": ObjectId(cluster_id)}
            )

    @pytest.mark.asyncio
    async def test_delete_cluster_not_found(self):
        """Test deleting non-existent cluster."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"

        # Mock get_cluster_by_id to return None (cluster not found)
        with patch.object(service, "get_cluster_by_id") as mock_get_cluster:
            mock_get_cluster.return_value = None

            result = await service.delete_cluster(cluster_id)
            assert result is False
            mock_get_cluster.assert_called_once_with(cluster_id)
            # delete_one should not be called if cluster not found
            mock_clusters_collection.delete_one.assert_not_called()

    def test_encrypt_decrypt_kube_config(self):
        """Test kube config encryption and decryption."""
        service = ClusterService()

        original_config = "apiVersion: v1\nkind: Config"

        # Test encryption
        encrypted = service._encrypt_kube_config(original_config)
        assert isinstance(encrypted, str)
        assert encrypted != original_config

        # Test decryption
        decrypted = service._decrypt_kube_config(encrypted)
        assert decrypted == original_config

    def test_validate_kube_config_valid(self):
        """Test kube config validation with valid config."""
        service = ClusterService()

        valid_config = """
apiVersion: v1
kind: Config
clusters:
- cluster:
    server: https://test.example.com
  name: test
contexts:
- context:
    cluster: test
    user: test
  name: test
current-context: test
users:
- name: test
  user:
    token: test
"""

        # Should not raise exception
        result = service._validate_kube_config(valid_config)
        assert result is True

    def test_validate_kube_config_invalid(self):
        """Test kube config validation with invalid config."""
        service = ClusterService()

        invalid_config = "invalid yaml content"

        with pytest.raises(ValueError):
            service._validate_kube_config(invalid_config)

    @pytest.mark.asyncio
    async def test_check_cluster_health_success(self):
        """Test successful cluster health check."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"

        # Mock get_cluster_by_id to return a cluster
        with patch.object(service, "get_cluster_by_id") as mock_get_cluster:
            from app.models.cluster import ClusterInDB

            mock_cluster = ClusterInDB(
                id=cluster_id,
                name="test-cluster",
                provider="aws",
                region="us-west-2",
                endpoint="https://k8s.test.com",
                encrypted_kube_config="encrypted_config",
                created_by="507f1f77bcf86cd799439012",
            )
            mock_get_cluster.return_value = mock_cluster

            # Mock get_decrypted_kubeconfig
            with patch.object(service, "get_decrypted_kubeconfig") as mock_decrypt:
                mock_decrypt.return_value = "apiVersion: v1\nkind: Config\nclusters:\n- cluster:\n    server: https://k8s.test.com\n  name: test"

                # Mock database update
                mock_clusters_collection.update_one.return_value = AsyncMock()

                result = await service.check_cluster_health(cluster_id)

                assert result["cluster_id"] == cluster_id
                assert result["status"] == "healthy"
                assert result["nodes_ready"] == 3  # Mock data from service
                assert result["nodes_total"] == 3  # Mock data from service
                assert result["cpu_usage"] == 45.2
                assert result["memory_usage"] == 62.1
                assert "response_time_ms" in result
                assert "available_resources" in result

                mock_get_cluster.assert_called_once_with(cluster_id)
                mock_decrypt.assert_called_once_with(cluster_id)

    @pytest.mark.asyncio
    async def test_check_cluster_health_unhealthy(self):
        """Test cluster health check for unhealthy cluster."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"

        # Mock get_cluster_by_id to return a cluster
        with patch.object(service, "get_cluster_by_id") as mock_get_cluster:
            from app.models.cluster import ClusterInDB

            mock_cluster = ClusterInDB(
                id=cluster_id,
                name="test-cluster",
                provider="aws",
                region="us-west-2",
                endpoint="https://k8s.test.com",
                encrypted_kube_config="encrypted_config",
                created_by="507f1f77bcf86cd799439012",
            )
            mock_get_cluster.return_value = mock_cluster

            # Mock get_decrypted_kubeconfig to raise an exception (simulating connection failure)
            with patch.object(service, "get_decrypted_kubeconfig") as mock_decrypt:
                mock_decrypt.side_effect = Exception("Connection failed")

                # Mock database update
                mock_clusters_collection.update_one.return_value = AsyncMock()

                result = await service.check_cluster_health(cluster_id)

                assert result["cluster_id"] == cluster_id
                assert result["status"] == "unhealthy"
                assert result["nodes_ready"] == 0
                assert result["nodes_total"] == 0
                assert "error_message" in result
                assert "Connection failed" in result["error_message"]
                assert len(result["errors"]) > 0

                mock_get_cluster.assert_called_once_with(cluster_id)
                mock_decrypt.assert_called_once_with(cluster_id)

    @pytest.mark.asyncio
    async def test_check_cluster_health_connection_error(self):
        """Test cluster health check with connection error."""
        service = ClusterService()
        mock_db = MagicMock()
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"

        # Mock get_cluster_by_id to return None (cluster not found)
        with patch.object(service, "get_cluster_by_id") as mock_get_cluster:
            mock_get_cluster.return_value = None

            result = await service.check_cluster_health(cluster_id)

            assert result["cluster_id"] == cluster_id
            assert result["status"] == "unhealthy"
            assert result["nodes_ready"] == 0
            assert result["nodes_total"] == 0
            assert result["error_message"] == "Cluster not found"
            assert "Cluster not found" in result["errors"]

            mock_get_cluster.assert_called_once_with(cluster_id)

    def test_get_available_regions(self):
        """Test getting available regions."""
        service = ClusterService()

        regions = service.get_available_regions()

        assert isinstance(regions, list)
        assert len(regions) > 0

        # Check region structure
        region = regions[0]
        assert hasattr(region, "name")
        assert hasattr(region, "display_name")
        assert hasattr(region, "provider")

    def test_get_regions_by_provider(self):
        """Test getting regions filtered by provider."""
        service = ClusterService()

        aws_regions = service.get_regions_by_provider("aws")
        gcp_regions = service.get_regions_by_provider("gcp")

        assert isinstance(aws_regions, list)
        assert isinstance(gcp_regions, list)
        assert len(aws_regions) > 0
        assert len(gcp_regions) > 0

        # Verify all regions belong to correct provider
        for region in aws_regions:
            assert region.provider == "aws"

        for region in gcp_regions:
            assert region.provider == "gcp"

    @pytest.mark.asyncio
    async def test_get_default_cluster(self):
        """Test getting default cluster."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        default_cluster_doc = {
            "_id": ObjectId("507f1f77bcf86cd799439011"),
            "name": "default-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "status": "active",
            "is_default": True,
            "created_at": datetime.now(timezone.utc),
        }
        mock_clusters_collection.find_one.return_value = default_cluster_doc

        result = await service.get_default_cluster()

        assert isinstance(result, ClusterInDB)
        assert result.is_default is True
        mock_clusters_collection.find_one.assert_called_once_with({"is_default": True})

    @pytest.mark.asyncio
    async def test_set_default_cluster(self):
        """Test setting default cluster."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        cluster_id = "507f1f77bcf86cd799439011"

        # Mock update operations
        mock_clusters_collection.update_many.return_value = MagicMock(modified_count=1)
        mock_clusters_collection.update_one.return_value = MagicMock(modified_count=1)

        result = await service.set_default_cluster(cluster_id)

        assert result is True
        # Verify all clusters set to not default, then target cluster set to default
        assert mock_clusters_collection.update_many.call_count == 1
        assert mock_clusters_collection.update_one.call_count == 1

    def test_cluster_service_encryption_key_generation(self):
        """Test encryption key generation from settings."""
        service = ClusterService()

        # Verify encryption key is generated from settings
        assert len(service.encryption_key) == 32
        assert service.cipher_suite is not None

    @pytest.mark.asyncio
    async def test_cluster_service_error_handling(self):
        """Test error handling in cluster service methods."""
        service = ClusterService()
        mock_db = MagicMock()
        mock_clusters_collection = AsyncMock()
        mock_db.clusters = mock_clusters_collection
        service.set_database(mock_db)

        # Test database error handling - list_clusters has graceful error handling
        # that returns empty list instead of raising exceptions
        mock_clusters_collection.find.side_effect = Exception("Database error")

        # This should not raise an exception, but return an empty list
        result = await service.list_clusters()
        assert result == []

        # Test that database not initialized raises proper error
        service_no_db = ClusterService()
        with pytest.raises(ValueError, match="Database not initialized"):
            await service_no_db.list_clusters()


# Create cluster service instance for testing
cluster_service = ClusterService()
