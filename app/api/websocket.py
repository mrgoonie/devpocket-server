import json
import uuid
from typing import Dict, Optional

import structlog
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream

from app.core.database import get_database
from app.core.security import verify_token
from app.middleware.rate_limiting import websocket_rate_limiter
from app.models.cluster import ClusterRegion
from app.models.user import UserInDB
from app.services.environment_service import environment_service
from app.services.pty_service import pty_manager
from app.services.tmux_service import tmux_manager

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

    async def send_user_message(self, message: str, user_id: str):
        """Send message to all connections of a specific user"""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                await self.send_personal_message(message, connection_id)

    async def broadcast_to_user(self, message: str, user_id: str):
        """Broadcast message to all connections of a specific user"""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id]:
                await self.send_personal_message(message, connection_id)

    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user"""
        if user_id in self.user_connections:
            return len(self.user_connections[user_id])
        return 0


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
    """WebSocket endpoint for PTY terminal access"""
    logger.info(f"WebSocket PTY handler called for environment: {environment_id}")
    connection_id = str(uuid.uuid4())
    user = None
    pty_session_id = None

    try:
        logger.info(
            f"WebSocket terminal: Starting PTY connection for env {environment_id}"
        )

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

        # Allow connections for running environments or environments currently installing
        if environment.status not in ["running", "installing"]:
            logger.error(
                f"WebSocket terminal: Environment not ready: {environment.status}"
            )
            await websocket.close(code=1008, reason="Environment not ready")
            return
        logger.info(f"WebSocket terminal: Environment status is {environment.status}")

        # Accept connection
        await connection_manager.connect(websocket, connection_id, str(user.id))
        websocket_rate_limiter.add_connection(str(user.id))

        # Create WebSocket session
        await environment_service.create_websocket_session(
            str(user.id), environment_id, connection_id
        )

        logger.info(f"Terminal WebSocket connected for environment {environment_id}")

        # Send welcome message
        welcome_msg = {
            "type": "welcome",
            "message": f"Connected to {environment.name}",
            "environment": {
                "id": str(environment.id),
                "name": environment.name,
                "template": environment.template.value,
                "status": environment.status.value,
                "installation_completed": environment.installation_completed,
                "pty_enabled": environment.status.value == "running",
            },
        }
        await connection_manager.send_personal_message(
            json.dumps(welcome_msg), connection_id
        )

        # Create or attach to tmux session only if environment is running
        tmux_session_id = None
        if (
            environment.status.value == "running"
        ):  # Compare with string directly, not enum value
            # Try to find existing tmux session for this environment
            existing_sessions = await tmux_manager.list_sessions(
                environment_id=environment_id
            )

            if existing_sessions:
                # Attach to existing session
                tmux_session_id = existing_sessions[0]
                logger.info(f"Attaching to existing tmux session: {tmux_session_id}")
            else:
                # Create new tmux session
                tmux_session_id = await tmux_manager.create_session(
                    environment_id=environment_id,
                    user_id=str(user.id),
                    session_name=f"devpocket_{environment_id}",
                    initial_command="cd /home/devpocket/workspace && bash",
                )

                if not tmux_session_id:
                    logger.error(f"Failed to create tmux session for {environment_id}")
                    await websocket.close(
                        code=1008, reason="Failed to create terminal session"
                    )
                    return

                logger.info(f"Created new tmux session: {tmux_session_id}")

            def tmux_output_callback(data: str):
                """Callback for tmux output"""
                try:
                    import asyncio

                    # Create output message
                    output_msg = {
                        "type": "output",
                        "data": data,
                    }

                    # Get the current event loop from the main thread
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Schedule the coroutine to run in the event loop
                            asyncio.create_task(
                                connection_manager.send_personal_message(
                                    json.dumps(output_msg), connection_id
                                )
                            )
                        else:
                            # If no loop is running, run it
                            loop.run_until_complete(
                                connection_manager.send_personal_message(
                                    json.dumps(output_msg), connection_id
                                )
                            )
                    except RuntimeError:
                        # No event loop available, create a new one
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            connection_manager.send_personal_message(
                                json.dumps(output_msg), connection_id
                            )
                        )
                        loop.close()
                except Exception as e:
                    logger.error(f"Error sending tmux output: {e}")

            # Attach to tmux session
            tmux_success = await tmux_manager.attach_to_session(
                tmux_session_id, tmux_output_callback
            )

            if not tmux_success:
                logger.error(f"Failed to attach to tmux session {tmux_session_id}")
                await websocket.close(
                    code=1008, reason="Failed to attach to terminal session"
                )
                return

            logger.info(f"Attached to tmux session: {tmux_session_id}")

            # Send initial session output to client
            initial_output = await tmux_manager.capture_session_output(tmux_session_id)
            if initial_output:
                await connection_manager.send_personal_message(
                    json.dumps({"type": "output", "data": initial_output}),
                    connection_id,
                )
        else:
            logger.info(
                f"Environment is installing, PTY session will be created once installation completes"
            )

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
                    # Terminal input - send to tmux only if session exists
                    if tmux_session_id:
                        input_data = message.get("data", "")
                        success = await tmux_manager.send_input(
                            tmux_session_id, input_data
                        )

                        if not success:
                            await connection_manager.send_personal_message(
                                json.dumps(
                                    {
                                        "type": "error",
                                        "message": "Failed to send input to terminal",
                                    }
                                ),
                                connection_id,
                            )
                    else:
                        # Environment is still installing
                        await connection_manager.send_personal_message(
                            json.dumps(
                                {
                                    "type": "info",
                                    "message": "Environment is still installing. Terminal will be available once installation completes.",
                                }
                            ),
                            connection_id,
                        )

                elif message.get("type") == "ping":
                    # Respond to ping
                    pong_response = {"type": "pong"}
                    await connection_manager.send_personal_message(
                        json.dumps(pong_response), connection_id
                    )

                elif message.get("type") == "resize":
                    # Handle terminal resize only if tmux session exists
                    if tmux_session_id:
                        cols = message.get("cols", 80)
                        rows = message.get("rows", 24)

                        success = await tmux_manager.resize_session(
                            tmux_session_id, cols, rows
                        )
                        logger.debug(
                            f"Terminal resize: {cols}x{rows}, success: {success}"
                        )
                    # Ignore resize requests for installing environments

            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                await connection_manager.send_personal_message(
                    json.dumps({"type": "error", "message": "Internal server error"}),
                    connection_id,
                )

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            await websocket.close(code=1008, reason="Internal server error")
        except Exception:
            pass

    finally:
        # Cleanup tmux session attachment (but keep session alive for persistence)
        if "tmux_session_id" in locals() and tmux_session_id:
            try:
                # Note: We don't kill the tmux session, just detach from it
                # This allows the session to persist for reconnection
                await tmux_manager.detach_from_session(
                    tmux_session_id, tmux_output_callback
                )
                logger.info(f"Detached from tmux session: {tmux_session_id}")
            except Exception as e:
                logger.error(f"Error detaching from tmux session: {e}")

        # Cleanup WebSocket
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
