import json
import uuid
from typing import Dict, Optional

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.database import get_database
from app.core.security import verify_token
from app.middleware.rate_limiting import websocket_rate_limiter
from app.models.cluster import ClusterRegion
from app.models.user import UserInDB
from app.services.environment_service import environment_service

logger = structlog.get_logger(__name__)
router = APIRouter()


class WebSocketConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, set] = {}  # user_id -> set of connection_ids

    async def connect(self, websocket: WebSocket, connection_id: str, user_id: str):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")

    def disconnect(self, connection_id: str, user_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def send_personal_message(self, message: str, connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")


# Global connection manager
connection_manager = WebSocketConnectionManager()


async def authenticate_websocket(token: str, db) -> Optional[UserInDB]:
    """Authenticate WebSocket connection"""
    try:
        if not token:
            return None

        # Verify token
        payload = verify_token(token)
        if payload is None:
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None

        # Get user from database
        from bson import ObjectId

        user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
        if user_doc is None:
            return None

        user = UserInDB(**user_doc)
        return user if user.is_active else None

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


@router.websocket("/terminal/{environment_id}")
async def websocket_terminal(
    websocket: WebSocket,
    environment_id: str,
    token: Optional[str] = Query(None),
    db=Depends(get_database),
):
    """WebSocket endpoint for terminal access"""
    logger.info(f"WebSocket handler called for environment: {environment_id}")
    connection_id = str(uuid.uuid4())
    user = None

    try:
        logger.info(f"WebSocket terminal: Starting connection for env {environment_id}")

        # Authenticate user
        logger.info(
            f"WebSocket terminal: Authenticating token: {token[:20] if token else 'None'}..."
        )
        user = await authenticate_websocket(token, db)
        if not user:
            logger.error("WebSocket terminal: Authentication failed")
            await websocket.close(code=1008, reason="Authentication failed")
            return
        logger.info(f"WebSocket terminal: User authenticated: {user.username}")

        # Check rate limits
        logger.info(f"WebSocket terminal: Checking rate limits for user {user.id}")
        if not websocket_rate_limiter.check_connection_limit(str(user.id)):
            logger.error(f"WebSocket terminal: Rate limit exceeded for user {user.id}")
            await websocket.close(code=1008, reason="Too many connections")
            return
        logger.info("WebSocket terminal: Rate limit check passed")

        # Verify environment access
        logger.info("WebSocket terminal: Verifying environment access")
        environment_service.set_database(db)
        environment = await environment_service.get_environment(
            environment_id, str(user.id)
        )
        if not environment:
            logger.error(
                f"WebSocket terminal: Environment {environment_id} not found for user {user.id}"
            )
            await websocket.close(code=1008, reason="Environment not found")
            return
        logger.info(f"WebSocket terminal: Environment found: {environment.name}")

        if environment.status != "running":
            logger.error(
                f"WebSocket terminal: Environment not running: {environment.status}"
            )
            await websocket.close(code=1008, reason="Environment not running")
            return
        logger.info("WebSocket terminal: Environment is running")

        # Get actual pod name from Kubernetes
        logger.info("WebSocket terminal: Getting actual pod name")
        actual_pod_name = await environment_service.get_actual_pod_name(environment)
        if not actual_pod_name:
            logger.error(
                f"WebSocket terminal: Pod not found for environment {environment_id}"
            )
            await websocket.close(code=1008, reason="Pod not found")
            return
        logger.info(f"WebSocket terminal: Actual pod found: {actual_pod_name}")

        # Accept connection
        await connection_manager.connect(websocket, connection_id, str(user.id))
        websocket_rate_limiter.add_connection(str(user.id))

        # Create WebSocket session
        await environment_service.create_websocket_session(
            str(user.id), environment_id, connection_id
        )

        logger.info(
            f"Terminal WebSocket connected for environment {environment_id}, pod: {actual_pod_name}"
        )

        # Send welcome message
        welcome_msg = {
            "type": "welcome",
            "message": f"Connected to {environment.name}",
            "environment": {
                "id": str(environment.id),
                "name": environment.name,
                "template": environment.template.value,
                "status": environment.status.value,
                "pod_name": actual_pod_name,
            },
        }
        await connection_manager.send_personal_message(
            json.dumps(welcome_msg), connection_id
        )

        # Set up Kubernetes exec connection
        import base64
        import os
        import tempfile

        from kubernetes import client, config as k8s_config
        from kubernetes.client.exceptions import ApiException

        from app.services.cluster_service import cluster_service

        # Get cluster configuration
        cluster_service.set_database(db)
        cluster = await cluster_service.get_cluster_by_region(
            ClusterRegion.SOUTHEAST_ASIA
        )
        if not cluster:
            await websocket.close(code=1008, reason="Cluster not available")
            return

        # Get decrypted kubeconfig
        kubeconfig_content = await cluster_service.get_decrypted_kubeconfig(cluster.id)
        if not kubeconfig_content:
            await websocket.close(code=1008, reason="Kubeconfig not available")
            return

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
            from kubernetes.client.configuration import Configuration

            config = Configuration.get_default_copy()
            config.verify_ssl = False
            config.ssl_ca_cert = None
            Configuration.set_default(config)

            # Initialize Kubernetes client
            v1_core = client.CoreV1Api()

            # Main message loop
            while True:
                try:
                    # Receive message from client
                    data = await websocket.receive_text()

                    # Check message rate limits
                    if not websocket_rate_limiter.check_message_rate(str(user.id)):
                        await connection_manager.send_personal_message(
                            json.dumps(
                                {
                                    "type": "error",
                                    "message": "Rate limit exceeded. Please slow down.",
                                }
                            ),
                            connection_id,
                        )
                        continue

                    # Parse message
                    try:
                        message = json.loads(data)
                    except json.JSONDecodeError:
                        # Treat as raw terminal input
                        message = {"type": "input", "data": data}

                    # Handle different message types
                    if message.get("type") == "input":
                        # Terminal input - execute command in pod
                        command = message.get("data", "")
                        try:
                            # Execute command in pod using kubectl exec
                            exec_response = v1_core.connect_get_namespaced_pod_exec(
                                name=actual_pod_name,
                                namespace=environment.namespace,
                                container="devpocket-env",
                                command=["/bin/bash", "-c", command],
                                stderr=True,
                                stdin=False,
                                stdout=True,
                                tty=False,
                            )

                            # Send command output back to client
                            response = {
                                "type": "output",
                                "data": f"$ {command}\n{exec_response}\n",
                            }
                            await connection_manager.send_personal_message(
                                json.dumps(response), connection_id
                            )

                        except ApiException as e:
                            error_response = {
                                "type": "output",
                                "data": f"$ {command}\nError: {e.reason}\n",
                            }
                            await connection_manager.send_personal_message(
                                json.dumps(error_response), connection_id
                            )
                        except Exception as e:
                            error_response = {
                                "type": "output",
                                "data": f"$ {command}\nError: {str(e)}\n",
                            }
                            await connection_manager.send_personal_message(
                                json.dumps(error_response), connection_id
                            )

                    elif message.get("type") == "ping":
                        # Respond to ping
                        pong_response = {"type": "pong"}
                        await connection_manager.send_personal_message(
                            json.dumps(pong_response), connection_id
                        )

                    elif message.get("type") == "resize":
                        # Handle terminal resize (placeholder)
                        logger.debug(f"Terminal resize: {message}")

                except WebSocketDisconnect:
                    logger.info(f"WebSocket client disconnected: {connection_id}")
                    break
                except Exception as e:
                    logger.error(f"WebSocket message error: {e}")
                    await connection_manager.send_personal_message(
                        json.dumps(
                            {"type": "error", "message": "Internal server error"}
                        ),
                        connection_id,
                    )

        finally:
            # Clean up temporary kubeconfig file
            if os.path.exists(kubeconfig_path):
                os.unlink(kubeconfig_path)

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1008, reason="Internal server error")
        except Exception:
            pass

    finally:
        # Cleanup
        connection_manager.disconnect(connection_id, str(user.id) if user else "")
        if user:
            websocket_rate_limiter.remove_connection(str(user.id))
            # Clean up WebSocket session
            try:
                await environment_service.cleanup_websocket_session(
                    str(user.id), environment_id, connection_id
                )
            except Exception as e:
                logger.error(f"Error cleaning up WebSocket session: {e}")


@router.websocket("/logs/{environment_id}")
async def websocket_logs(
    websocket: WebSocket,
    environment_id: str,
    token: Optional[str] = Query(None),
    db=Depends(get_database),
):
    """WebSocket endpoint for environment logs"""
    connection_id = str(uuid.uuid4())
    user = None

    try:
        # Authenticate user
        user = await authenticate_websocket(token, db)
        if not user:
            await websocket.close(code=1008, reason="Authentication failed")
            return

        # Check rate limits
        if not websocket_rate_limiter.check_connection_limit(str(user.id)):
            await websocket.close(code=1008, reason="Too many connections")
            return

        # Verify environment access
        environment_service.set_database(db)
        environment = await environment_service.get_environment(
            environment_id, str(user.id)
        )
        if not environment:
            await websocket.close(code=1008, reason="Environment not found")
            return

        # Accept connection
        await connection_manager.connect(websocket, connection_id, str(user.id))

        # Create WebSocket session
        await environment_service.create_websocket_session(
            str(user.id), environment_id, connection_id
        )

        logger.info(f"Logs WebSocket connected for environment {environment_id}")

        # Send welcome message
        welcome_msg = {
            "type": "welcome",
            "message": f"Connected to {environment.name} logs",
        }
        await connection_manager.send_personal_message(
            json.dumps(welcome_msg), connection_id
        )

        # Main message loop for log streaming
        while True:
            try:
                # For now, this is a placeholder - in a real implementation,
                # you would stream actual logs from the environment
                data = await websocket.receive_text()
                message = json.loads(data)

                if message.get("type") == "ping":
                    pong_response = {"type": "pong"}
                    await connection_manager.send_personal_message(
                        json.dumps(pong_response), connection_id
                    )

            except WebSocketDisconnect:
                logger.info(f"WebSocket logs client disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket logs error: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket logs connection error: {e}")
        try:
            await websocket.close(code=1008, reason="Internal server error")
        except Exception:
            pass

    finally:
        # Cleanup
        connection_manager.disconnect(connection_id, str(user.id) if user else "")
        if user:
            websocket_rate_limiter.remove_connection(str(user.id))
            # Clean up WebSocket session
            try:
                await environment_service.cleanup_websocket_session(
                    str(user.id), environment_id, connection_id
                )
            except Exception as e:
                logger.error(f"Error cleaning up WebSocket logs session: {e}")
