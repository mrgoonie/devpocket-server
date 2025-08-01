import asyncio
import base64
import json
import os
import tempfile
from datetime import datetime
from typing import Callable, Optional

import structlog
from kubernetes import client, config as k8s_config
from kubernetes.client.exceptions import ApiException
from kubernetes.watch import Watch

logger = structlog.get_logger(__name__)


class KubernetesLogService:
    """Service for streaming Kubernetes pod logs"""

    def __init__(self):
        self.db = None
        self.active_streams = {}  # environment_id -> stream task

    def set_database(self, db):
        """Set database instance"""
        self.db = db

    async def stream_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        environment_id: str,
        user_id: str,
        on_log_line: Callable[[str], None],
        on_complete: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        completion_pattern: str = "sleep infinity",
        timeout: int = 600,  # 10 minutes default
    ):
        """Stream logs from a pod and call callbacks for each line

        Args:
            namespace: Kubernetes namespace
            pod_name: Name of the pod
            environment_id: Environment ID for tracking
            user_id: User ID for tracking
            on_log_line: Callback for each log line
            on_complete: Callback when installation completes
            on_error: Callback on error
            completion_pattern: Pattern to detect installation completion
            timeout: Timeout in seconds
        """
        from app.services.cluster_service import cluster_service

        try:
            # Store the stream task reference
            self.active_streams[environment_id] = asyncio.current_task()

            # Get cluster configuration
            cluster_service.set_database(self.db)
            from app.models.cluster import ClusterRegion

            cluster = await cluster_service.get_cluster_by_region(
                ClusterRegion.SOUTHEAST_ASIA
            )
            if not cluster:
                raise Exception("No active cluster found for Southeast Asia region")

            # Get decrypted kubeconfig
            kubeconfig_content = await cluster_service.get_decrypted_kubeconfig(
                cluster.id
            )
            if not kubeconfig_content:
                raise Exception("Failed to get kubeconfig for cluster")

            # Decode base64 kubeconfig
            kubeconfig_yaml = base64.b64decode(kubeconfig_content).decode("utf-8")

            # Create temporary kubeconfig file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as temp_kubeconfig:
                temp_kubeconfig.write(kubeconfig_yaml)
                kubeconfig_path = temp_kubeconfig.name

            try:
                # Load kubeconfig
                k8s_config.load_kube_config(config_file=kubeconfig_path)

                # Disable SSL verification for testing
                import ssl

                from kubernetes.client.configuration import Configuration

                config = Configuration.get_default_copy()
                config.verify_ssl = False
                config.ssl_ca_cert = None
                Configuration.set_default(config)

                # Initialize Kubernetes client
                v1_core = client.CoreV1Api()

                # Wait for pod to be ready first
                logger.info(f"Waiting for pod {pod_name} to be ready...")
                pod_ready = await self._wait_for_pod_ready(
                    v1_core, namespace, pod_name, timeout=120
                )

                if not pod_ready:
                    error_msg = f"Pod {pod_name} failed to become ready"
                    logger.error(error_msg)
                    if on_error:
                        await on_error(error_msg)
                    return

                # Find the actual pod name from deployment
                pods = v1_core.list_namespaced_pod(
                    namespace=namespace, label_selector=f"environment={pod_name}"
                )

                if not pods.items:
                    error_msg = f"No pods found for environment {pod_name}"
                    logger.error(error_msg)
                    if on_error:
                        await on_error(error_msg)
                    return

                actual_pod_name = pods.items[0].metadata.name
                logger.info(f"Found pod: {actual_pod_name}, starting log stream...")

                # Stream logs using watch
                watch = Watch()
                start_time = asyncio.get_event_loop().time()

                # Create async wrapper for the stream
                async def log_stream():
                    try:
                        # Use follow=True to stream logs as they appear
                        for line in watch.stream(
                            v1_core.read_namespaced_pod_log,
                            name=actual_pod_name,
                            namespace=namespace,
                            follow=True,
                            _preload_content=False,
                            timestamps=False,
                        ):
                            # Check timeout
                            if asyncio.get_event_loop().time() - start_time > timeout:
                                logger.warning(
                                    f"Log streaming timeout for pod {actual_pod_name}"
                                )
                                break

                            # Decode the line if it's bytes, handle encoding errors gracefully
                            if isinstance(line, bytes):
                                try:
                                    line = line.decode("utf-8")
                                except UnicodeDecodeError:
                                    # Try with error handling for non-UTF8 bytes
                                    line = line.decode("utf-8", errors="replace")

                            # Strip newline and send to callback
                            line = line.rstrip("\n")
                            if line:  # Only send non-empty lines
                                await on_log_line(line)

                                # Check for completion pattern
                                if completion_pattern in line:
                                    logger.info(
                                        f"Installation completed for pod {actual_pod_name}"
                                    )
                                    if on_complete:
                                        await on_complete()
                                    break

                    except Exception as e:
                        logger.error(f"Error streaming logs: {e}")
                        if on_error:
                            await on_error(str(e))
                    finally:
                        watch.stop()

                # Run the log stream
                await log_stream()

            finally:
                # Clean up temporary kubeconfig file
                if os.path.exists(kubeconfig_path):
                    os.unlink(kubeconfig_path)

        except Exception as e:
            logger.error(f"Error in stream_pod_logs: {e}")
            if on_error:
                await on_error(str(e))
        finally:
            # Remove from active streams
            if environment_id in self.active_streams:
                del self.active_streams[environment_id]

    async def _wait_for_pod_ready(
        self,
        v1_core: client.CoreV1Api,
        namespace: str,
        pod_name: str,
        timeout: int = 120,
    ) -> bool:
        """Wait for a pod to be ready"""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                # List pods with the environment label
                pods = v1_core.list_namespaced_pod(
                    namespace=namespace, label_selector=f"environment={pod_name}"
                )

                if pods.items:
                    pod = pods.items[0]
                    # Check if pod is ready
                    if pod.status.phase == "Running":
                        # Check container status
                        if pod.status.container_statuses:
                            container_status = pod.status.container_statuses[0]
                            if container_status.ready:
                                return True
                            elif container_status.state.waiting:
                                reason = container_status.state.waiting.reason
                                if reason in [
                                    "CrashLoopBackOff",
                                    "ImagePullBackOff",
                                    "ErrImagePull",
                                ]:
                                    logger.error(f"Pod failed with reason: {reason}")
                                    return False

            except ApiException as e:
                logger.error(f"Error checking pod status: {e}")

            # Wait before next check
            await asyncio.sleep(5)

        return False

    def stop_stream(self, environment_id: str):
        """Stop an active log stream"""
        if environment_id in self.active_streams:
            task = self.active_streams[environment_id]
            if not task.done():
                task.cancel()
            del self.active_streams[environment_id]
            logger.info(f"Stopped log stream for environment {environment_id}")

    def is_streaming(self, environment_id: str) -> bool:
        """Check if log streaming is active for an environment"""
        return environment_id in self.active_streams


# Global instance
kubernetes_log_service = KubernetesLogService()
