from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.websockets import WebSocketState
import asyncio
import json
import uuid
import structlog
from typing import Dict, Optional

from app.core.database import get_database
from app.services.environment_service import environment_service
from app.middleware.auth import get_current_user
from app.middleware.rate_limiting import websocket_rate_limiter
from app.core.security import verify_token
from app.models.user import UserInDB

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
            websocket = self.active_connections[connection_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_text(message)
    
    async def send_binary_message(self, data: bytes, connection_id: str):
        """Send binary data to specific connection"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_bytes(data)
    
    def get_user_connections(self, user_id: str) -> set:
        """Get all connection IDs for a user"""
        return self.user_connections.get(user_id, set())

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
        user_doc = await db.users.find_one({"_id": user_id})
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
    db=Depends(get_database)
):
    """WebSocket endpoint for terminal access"""
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
        environment = await environment_service.get_environment(environment_id, str(user.id))
        if not environment:
            await websocket.close(code=1008, reason="Environment not found")
            return
        
        if environment.status != "running":
            await websocket.close(code=1008, reason="Environment not running")
            return
        
        # Accept connection
        await connection_manager.connect(websocket, connection_id, str(user.id))
        websocket_rate_limiter.add_connection(str(user.id))
        
        # Create WebSocket session
        await environment_service.create_websocket_session(
            str(user.id), 
            environment_id, 
            connection_id
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
                "status": environment.status.value
            }
        }
        await connection_manager.send_personal_message(
            json.dumps(welcome_msg), 
            connection_id
        )
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                
                # Check message rate limits
                if not websocket_rate_limiter.check_message_rate(str(user.id)):
                    await connection_manager.send_personal_message(
                        json.dumps({
                            "type": "error",
                            "message": "Rate limit exceeded. Please slow down."
                        }),
                        connection_id
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
                    # Terminal input - forward to container
                    # In a real implementation, this would be sent to the actual container
                    # For now, we'll echo it back as a simulation
                    response = {
                        "type": "output",
                        "data": f"$ {message.get('data', '')}\nCommand executed (simulated)\n"
                    }
                    await connection_manager.send_personal_message(
                        json.dumps(response), 
                        connection_id
                    )
                
                elif message.get("type") == "resize":
                    # Terminal resize
                    cols = message.get("cols", 80)
                    rows = message.get("rows", 24)
                    logger.info(f"Terminal resize: {cols}x{rows}")
                    
                elif message.get("type") == "ping":
                    # Ping/pong for keepalive
                    await connection_manager.send_personal_message(
                        json.dumps({"type": "pong"}),
                        connection_id
                    )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket client disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
                await connection_manager.send_personal_message(
                    json.dumps({
                        "type": "error", 
                        "message": "Internal server error"
                    }),
                    connection_id
                )
    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # Cleanup
        if user:
            connection_manager.disconnect(connection_id, str(user.id))
            websocket_rate_limiter.remove_connection(str(user.id))
            await environment_service.remove_websocket_session(connection_id)

@router.websocket("/logs/{environment_id}")
async def websocket_logs(
    websocket: WebSocket,
    environment_id: str,
    token: Optional[str] = Query(None),
    follow: bool = Query(True),
    db=Depends(get_database)
):
    """WebSocket endpoint for streaming environment logs"""
    connection_id = str(uuid.uuid4())
    user = None
    
    try:
        # Authenticate user
        user = await authenticate_websocket(token, db)
        if not user:
            await websocket.close(code=1008, reason="Authentication failed")
            return
        
        # Verify environment access
        environment_service.set_database(db)
        environment = await environment_service.get_environment(environment_id, str(user.id))
        if not environment:
            await websocket.close(code=1008, reason="Environment not found")
            return
        
        # Accept connection
        await connection_manager.connect(websocket, connection_id, str(user.id))
        
        logger.info(f"Logs WebSocket connected for environment {environment_id}")
        
        # Send initial logs (simulated)
        initial_logs = [
            "2024-01-01 12:00:00 [INFO] Environment starting...",
            "2024-01-01 12:00:01 [INFO] Container initialized",
            "2024-01-01 12:00:02 [INFO] Ready for connections",
        ]
        
        for log_line in initial_logs:
            await connection_manager.send_personal_message(
                json.dumps({
                    "type": "log",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "level": "info",
                    "message": log_line
                }),
                connection_id
            )
        
        if follow:
            # Keep connection alive and simulate new logs
            while True:
                await asyncio.sleep(30)  # Send a log every 30 seconds
                
                if connection_id not in connection_manager.active_connections:
                    break
                
                # Simulate a new log entry
                await connection_manager.send_personal_message(
                    json.dumps({
                        "type": "log",
                        "timestamp": "2024-01-01T12:00:00Z",
                        "level": "info",
                        "message": "Heartbeat - system running normally"
                    }),
                    connection_id
                )
        else:
            # Just send logs and close
            await asyncio.sleep(1)
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1000, reason="Log stream complete")
    
    except WebSocketDisconnect:
        logger.info(f"Logs WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Logs WebSocket error: {e}")
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    finally:
        if user:
            connection_manager.disconnect(connection_id, str(user.id))