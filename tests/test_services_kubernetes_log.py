"""Simplified tests for kubernetes log service."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.kubernetes_log_service import KubernetesLogService


class TestKubernetesLogService:
    """Test KubernetesLogService class."""

    def test_kubernetes_log_service_init(self):
        """Test KubernetesLogService initialization."""
        service = KubernetesLogService()

        assert service.db is None
        assert service.active_streams == {}

    def test_set_database(self):
        """Test setting database instance."""
        service = KubernetesLogService()
        mock_db = MagicMock()

        service.set_database(mock_db)
        assert service.db == mock_db

    def test_stop_stream_active(self):
        """Test stopping an active stream."""
        service = KubernetesLogService()
        environment_id = "env_123"

        # Mock active task
        mock_task = MagicMock()
        mock_task.done.return_value = False
        service.active_streams[environment_id] = mock_task

        service.stop_stream(environment_id)

        mock_task.cancel.assert_called_once()
        assert environment_id not in service.active_streams

    def test_is_streaming_active(self):
        """Test checking if streaming is active."""
        service = KubernetesLogService()
        environment_id = "env_123"

        # No active streams initially
        assert not service.is_streaming(environment_id)

        # Add active stream
        service.active_streams[environment_id] = MagicMock()
        assert service.is_streaming(environment_id)

    @pytest.mark.asyncio
    async def test_wait_for_pod_ready_success(self):
        """Test successful pod ready wait."""
        service = KubernetesLogService()
        mock_v1_core = MagicMock()

        # Mock pod response - ready pod
        mock_pod = MagicMock()
        mock_pod.status.phase = "Running"
        mock_pod.status.container_statuses = [MagicMock()]
        mock_pod.status.container_statuses[0].ready = True

        mock_pods = MagicMock()
        mock_pods.items = [mock_pod]
        mock_v1_core.list_namespaced_pod.return_value = mock_pods

        result = await service._wait_for_pod_ready(
            mock_v1_core, "default", "test-pod", timeout=10
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_pod_ready_timeout(self):
        """Test pod ready wait timeout."""
        service = KubernetesLogService()
        mock_v1_core = MagicMock()

        # Mock pod response - not ready pod
        mock_pod = MagicMock()
        mock_pod.status.phase = "Pending"
        mock_pod.status.container_statuses = []

        mock_pods = MagicMock()
        mock_pods.items = [mock_pod]
        mock_v1_core.list_namespaced_pod.return_value = mock_pods

        # Use short timeout for test
        result = await service._wait_for_pod_ready(
            mock_v1_core, "default", "test-pod", timeout=1
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_stream_pod_logs_exception_handling(self):
        """Test exception handling in stream_pod_logs method."""
        service = KubernetesLogService()
        mock_db = MagicMock()
        service.set_database(mock_db)

        mock_on_error = AsyncMock()

        # Cause an exception by setting a bad environment_id that causes asyncio.current_task() to fail
        with patch("asyncio.current_task", side_effect=Exception("Task error")):
            await service.stream_pod_logs(
                namespace="default",
                pod_name="test-pod",
                environment_id="env_123",
                user_id="user_456",
                on_log_line=AsyncMock(),
                on_error=mock_on_error,
            )

            # Verify error callback was called
            mock_on_error.assert_called_once()
            error_msg = mock_on_error.call_args[0][0]
            assert "Task error" in error_msg

    @pytest.mark.asyncio
    async def test_stream_pod_logs_cleans_up_active_streams(self):
        """Test that stream_pod_logs cleans up active streams on completion."""
        service = KubernetesLogService()
        mock_db = MagicMock()
        service.set_database(mock_db)

        environment_id = "env_123"

        # Mock current task
        mock_task = MagicMock()
        with patch("asyncio.current_task", return_value=mock_task):
            # Cause an immediate exception to trigger cleanup
            with patch(
                "app.services.cluster_service.cluster_service"
            ) as mock_cluster_service:
                mock_cluster_service.set_database.side_effect = Exception("Test error")

                await service.stream_pod_logs(
                    namespace="default",
                    pod_name="test-pod",
                    environment_id=environment_id,
                    user_id="user_456",
                    on_log_line=AsyncMock(),
                    on_error=AsyncMock(),
                )

                # Verify active stream was cleaned up
                assert environment_id not in service.active_streams


# Global instance for testing
kubernetes_log_service = KubernetesLogService()
