"""Tests for cluster API endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.cluster import ClusterRegion


class TestClustersAPI:
    """Test cluster API endpoints."""

    @pytest.mark.asyncio
    async def test_create_cluster_admin_success(self, client: AsyncClient, admin_user):
        """Test successful cluster creation by admin."""
        cluster_data = {
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "description": "Test cluster",
            "kube_config": "apiVersion: v1\nkind: Config",
            "is_default": False,
        }

        with patch(
            "app.services.cluster_service.cluster_service.create_cluster"
        ) as mock_create:
            # Mock the created cluster response
            from datetime import datetime, timezone

            mock_cluster = MagicMock()
            mock_cluster.name = "test-cluster"
            mock_cluster.provider = "aws"
            mock_cluster.region = "us-west-2"
            mock_cluster.status = "active"
            mock_cluster.is_default = False
            mock_cluster.model_dump.return_value = {
                "id": "507f1f77bcf86cd799439011",
                "name": "test-cluster",
                "provider": "aws",
                "region": "us-west-2",
                "status": "active",
                "is_default": False,
                "encrypted_kube_config": "encrypted_config",
                "created_by": "admin_id",
                "environments_count": 0,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "description": "Test cluster",
                "endpoint": "https://k8s.test.com",
            }
            mock_create.return_value = mock_cluster

            response = await client.post(
                "/api/v1/clusters", json=cluster_data, headers=admin_user["headers"]
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "test-cluster"
            assert data["provider"] == "aws"
            assert "encrypted_kube_config" not in data  # Should be removed
            assert "created_by" not in data  # Should be removed  # Should be removed

    @pytest.mark.asyncio
    async def test_create_cluster_non_admin(
        self, client: AsyncClient, authenticated_user
    ):
        """Test cluster creation fails for non-admin users."""
        cluster_data = {
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "kube_config": "apiVersion: v1\nkind: Config",
        }

        response = await client.post(
            "/api/v1/clusters", json=cluster_data, headers=authenticated_user["headers"]
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_cluster_unauthenticated(self, client: AsyncClient):
        """Test cluster creation fails for unauthenticated users."""
        cluster_data = {
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "kube_config": "apiVersion: v1\nkind: Config",
        }

        response = await client.post("/api/v1/clusters", json=cluster_data)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_cluster_validation_error(
        self, client: AsyncClient, admin_user
    ):
        """Test cluster creation with validation errors."""
        # Missing required fields
        response = await client.post(
            "/api/v1/clusters", json={}, headers=admin_user["headers"]
        )
        assert response.status_code == 422

        # Invalid data
        response = await client.post(
            "/api/v1/clusters",
            json={"name": "", "provider": "invalid"},
            headers=admin_user["headers"],
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_cluster_service_error(self, client: AsyncClient, admin_user):
        """Test cluster creation with service error."""
        cluster_data = {
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "kube_config": "apiVersion: v1\nkind: Config",
        }

        with patch(
            "app.services.cluster_service.cluster_service.create_cluster"
        ) as mock_create:
            mock_create.side_effect = ValueError("Cluster already exists")

            response = await client.post(
                "/api/v1/clusters", json=cluster_data, headers=admin_user["headers"]
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_clusters_success(self, client: AsyncClient, authenticated_user):
        """Test successful cluster listing."""
        with patch(
            "app.services.cluster_service.cluster_service.list_clusters"
        ) as mock_list:
            from datetime import datetime, timezone

            from app.models.cluster import ClusterInDB

            mock_clusters = [
                ClusterInDB(
                    id="507f1f77bcf86cd799439011",
                    name="cluster1",
                    provider="aws",
                    region="us-west-2",
                    description="Test cluster 1",
                    endpoint="https://k8s1.test.com",
                    encrypted_kube_config="encrypted_config_1",
                    created_by="507f1f77bcf86cd799439020",
                    status="active",
                    is_default=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ),
                ClusterInDB(
                    id="507f1f77bcf86cd799439012",
                    name="cluster2",
                    provider="gcp",
                    region="us-central1",
                    description="Test cluster 2",
                    endpoint="https://k8s2.test.com",
                    encrypted_kube_config="encrypted_config_2",
                    created_by="507f1f77bcf86cd799439021",
                    status="active",
                    is_default=False,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ),
            ]
            mock_list.return_value = mock_clusters

            response = await client.get(
                "/api/v1/clusters", headers=authenticated_user["headers"]
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "cluster1"
            assert data[1]["name"] == "cluster2"

    @pytest.mark.asyncio
    async def test_list_clusters_with_filters(
        self, client: AsyncClient, authenticated_user
    ):
        """Test cluster listing with filters."""
        with patch(
            "app.services.cluster_service.cluster_service.list_clusters"
        ) as mock_list:
            mock_list.return_value = []

            response = await client.get(
                "/api/v1/clusters?region=us-west-2&provider=aws",
                headers=authenticated_user["headers"],
            )

            assert response.status_code == 200
            mock_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_clusters_unauthenticated(self, client: AsyncClient):
        """Test cluster listing fails for unauthenticated users."""
        response = await client.get("/api/v1/clusters")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_regions(self, client: AsyncClient, authenticated_user):
        """Test getting available regions."""
        response = await client.get(
            "/api/v1/clusters/regions", headers=authenticated_user["headers"]
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Should contain valid region data
        region = data[0]
        assert "name" in region
        assert "display_name" in region
        assert "provider" in region

    @pytest.mark.asyncio
    async def test_get_regions_unauthenticated(self, client: AsyncClient):
        """Test getting regions fails for unauthenticated users."""
        response = await client.get("/api/v1/clusters/regions")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_cluster_by_id_success(
        self, client: AsyncClient, authenticated_user
    ):
        """Test successful cluster retrieval by ID."""
        cluster_id = "507f1f77bcf86cd799439011"

        with patch(
            "app.services.cluster_service.cluster_service.get_cluster_by_id"
        ) as mock_get:
            from datetime import datetime, timezone

            from app.models.cluster import ClusterInDB

            mock_cluster = ClusterInDB(
                id=cluster_id,
                name="test-cluster",
                provider="aws",
                region="us-west-2",
                description="Test cluster",
                endpoint="https://k8s.test.com",
                encrypted_kube_config="encrypted_config",
                created_by="507f1f77bcf86cd799439020",
                status="active",
                is_default=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_get.return_value = mock_cluster

            response = await client.get(
                f"/api/v1/clusters/{cluster_id}", headers=authenticated_user["headers"]
            )

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test-cluster"

    @pytest.mark.asyncio
    async def test_get_cluster_not_found(self, client: AsyncClient, authenticated_user):
        """Test cluster retrieval with non-existent ID."""
        cluster_id = "507f1f77bcf86cd799439999"

        with patch(
            "app.services.cluster_service.cluster_service.get_cluster"
        ) as mock_get:
            mock_get.return_value = None

            response = await client.get(
                f"/api/v1/clusters/{cluster_id}", headers=authenticated_user["headers"]
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_cluster_admin_success(self, client: AsyncClient, admin_user):
        """Test successful cluster update by admin."""
        cluster_id = "507f1f77bcf86cd799439011"
        update_data = {"description": "Updated description", "status": "maintenance"}

        with patch(
            "app.services.cluster_service.cluster_service.update_cluster"
        ) as mock_update:
            from datetime import datetime, timezone

            from app.models.cluster import ClusterInDB

            mock_cluster = ClusterInDB(
                id=cluster_id,
                name="test-cluster",
                provider="aws",
                region="us-west-2",
                description="Updated description",
                endpoint="https://k8s.test.com",
                encrypted_kube_config="encrypted_config",
                created_by="507f1f77bcf86cd799439020",
                status="maintenance",
                is_default=False,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            mock_update.return_value = mock_cluster

            response = await client.put(
                f"/api/v1/clusters/{cluster_id}",
                json=update_data,
                headers=admin_user["headers"],
            )

            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Updated description"
            assert data["status"] == "maintenance"

    @pytest.mark.asyncio
    async def test_update_cluster_non_admin(
        self, client: AsyncClient, authenticated_user
    ):
        """Test cluster update fails for non-admin users."""
        cluster_id = "507f1f77bcf86cd799439011"

        response = await client.put(
            f"/api/v1/clusters/{cluster_id}",
            json={"description": "Updated"},
            headers=authenticated_user["headers"],
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_cluster_not_found(self, client: AsyncClient, admin_user):
        """Test updating non-existent cluster."""
        cluster_id = "507f1f77bcf86cd799439999"

        with patch(
            "app.services.cluster_service.cluster_service.update_cluster"
        ) as mock_update:
            mock_update.return_value = None

            response = await client.put(
                f"/api/v1/clusters/{cluster_id}",
                json={"description": "Updated"},
                headers=admin_user["headers"],
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_cluster_admin_success(self, client: AsyncClient, admin_user):
        """Test successful cluster deletion by admin."""
        cluster_id = "507f1f77bcf86cd799439011"

        with patch(
            "app.services.cluster_service.cluster_service.delete_cluster"
        ) as mock_delete:
            mock_delete.return_value = True

            response = await client.delete(
                f"/api/v1/clusters/{cluster_id}", headers=admin_user["headers"]
            )

            assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_cluster_non_admin(
        self, client: AsyncClient, authenticated_user
    ):
        """Test cluster deletion fails for non-admin users."""
        cluster_id = "507f1f77bcf86cd799439011"

        response = await client.delete(
            f"/api/v1/clusters/{cluster_id}", headers=authenticated_user["headers"]
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_cluster_not_found(self, client: AsyncClient, admin_user):
        """Test deleting non-existent cluster."""
        cluster_id = "507f1f77bcf86cd799439999"

        with patch(
            "app.services.cluster_service.cluster_service.delete_cluster"
        ) as mock_delete:
            mock_delete.return_value = False

            response = await client.delete(
                f"/api/v1/clusters/{cluster_id}", headers=admin_user["headers"]
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cluster_health_check_success(
        self, client: AsyncClient, authenticated_user
    ):
        """Test successful cluster health check."""
        cluster_id = "507f1f77bcf86cd799439011"

        with patch(
            "app.services.cluster_service.cluster_service.check_cluster_health"
        ) as mock_health:
            mock_health.return_value = {
                "cluster_id": cluster_id,
                "status": "healthy",
                "last_check": "2024-01-01T00:00:00Z",
                "nodes_ready": 3,
                "nodes_total": 3,
                "cpu_usage": 45.2,
                "memory_usage": 62.1,
                "errors": [],
            }

            response = await client.get(
                f"/api/v1/clusters/{cluster_id}/health",
                headers=authenticated_user["headers"],
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["nodes_ready"] == 3
            assert data["cpu_usage"] == 45.2

    @pytest.mark.asyncio
    async def test_cluster_health_check_unhealthy(
        self, client: AsyncClient, authenticated_user
    ):
        """Test cluster health check for unhealthy cluster."""
        cluster_id = "507f1f77bcf86cd799439011"

        with patch(
            "app.services.cluster_service.cluster_service.check_cluster_health"
        ) as mock_health:
            mock_health.return_value = {
                "cluster_id": cluster_id,
                "status": "unhealthy",
                "last_check": "2024-01-01T00:00:00Z",
                "nodes_ready": 1,
                "nodes_total": 3,
                "cpu_usage": 95.5,
                "memory_usage": 89.3,
                "errors": ["Node node-2 is not ready", "Node node-3 is not ready"],
            }

            response = await client.get(
                f"/api/v1/clusters/{cluster_id}/health",
                headers=authenticated_user["headers"],
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert len(data["errors"]) == 2

    @pytest.mark.asyncio
    async def test_cluster_health_check_not_found(
        self, client: AsyncClient, authenticated_user
    ):
        """Test health check for non-existent cluster."""
        cluster_id = "507f1f77bcf86cd799439999"

        with patch(
            "app.services.cluster_service.cluster_service.check_cluster_health"
        ) as mock_health:
            mock_health.side_effect = Exception("Cluster not found")

            response = await client.get(
                f"/api/v1/clusters/{cluster_id}/health",
                headers=authenticated_user["headers"],
            )

            assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_cluster_endpoints_error_handling(
        self, client: AsyncClient, admin_user
    ):
        """Test error handling in cluster endpoints."""
        cluster_data = {
            "name": "test-cluster",
            "provider": "aws",
            "region": "us-west-2",
            "kube_config": "apiVersion: v1\nkind: Config",
        }

        # Test service exception handling
        with patch(
            "app.services.cluster_service.cluster_service.create_cluster"
        ) as mock_create:
            mock_create.side_effect = Exception("Unexpected error")

            response = await client.post(
                "/api/v1/clusters", json=cluster_data, headers=admin_user["headers"]
            )

            assert response.status_code == 500
