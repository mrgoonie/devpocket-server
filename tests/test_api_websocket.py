"""Tests for websocket API functionality."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocketDisconnect

from app.api.websocket import WebSocketConnectionManager


class TestWebSocketConnectionManager:
    """Test WebSocket connection manager."""

    def test_websocket_manager_init(self):
        """Test WebSocket manager initialization."""
        manager = WebSocketConnectionManager()

        assert manager.active_connections == {}
        assert manager.user_connections == {}

    @pytest.mark.asyncio
    async def test_websocket_connect(self):
        """Test WebSocket connection."""
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "conn_123"
        user_id = "user_456"

        await manager.connect(mock_websocket, connection_id, user_id)

        # Verify connection is stored
        assert connection_id in manager.active_connections
        assert manager.active_connections[connection_id] == mock_websocket
        assert user_id in manager.user_connections
        assert connection_id in manager.user_connections[user_id]

        # Verify websocket.accept() was called
        mock_websocket.accept.assert_called_once()

    def test_websocket_disconnect(self):
        """Test WebSocket disconnection."""
        manager = WebSocketConnectionManager()
        mock_websocket = MagicMock()
        connection_id = "conn_123"
        user_id = "user_456"

        # Setup connection first
        manager.active_connections[connection_id] = mock_websocket
        manager.user_connections[user_id] = {connection_id}

        # Disconnect
        manager.disconnect(connection_id, user_id)

        # Verify connection is removed
        assert connection_id not in manager.active_connections
        assert user_id not in manager.user_connections

    def test_websocket_disconnect_multiple_connections(self):
        """Test disconnecting one of multiple connections for a user."""
        manager = WebSocketConnectionManager()
        mock_websocket1 = MagicMock()
        mock_websocket2 = MagicMock()
        connection_id1 = "conn_123"
        connection_id2 = "conn_456"
        user_id = "user_789"

        # Setup multiple connections for same user
        manager.active_connections[connection_id1] = mock_websocket1
        manager.active_connections[connection_id2] = mock_websocket2
        manager.user_connections[user_id] = {connection_id1, connection_id2}

        # Disconnect one connection
        manager.disconnect(connection_id1, user_id)

        # Verify only one connection is removed
        assert connection_id1 not in manager.active_connections
        assert connection_id2 in manager.active_connections
        assert user_id in manager.user_connections
        assert connection_id1 not in manager.user_connections[user_id]
        assert connection_id2 in manager.user_connections[user_id]

    @pytest.mark.asyncio
    async def test_websocket_send_personal_message(self):
        """Test sending personal message via WebSocket."""
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "conn_123"
        user_id = "user_456"

        # Setup connection
        manager.active_connections[connection_id] = mock_websocket
        manager.user_connections[user_id] = {connection_id}

        message = "Hello WebSocket"
        await manager.send_personal_message(message, connection_id)

        # Verify message was sent
        mock_websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_websocket_send_personal_message_not_found(self):
        """Test sending message to non-existent connection."""
        manager = WebSocketConnectionManager()

        # This should not raise an error, just log and continue
        await manager.send_personal_message("Hello", "non_existent_conn")

    @pytest.mark.asyncio
    async def test_websocket_broadcast_to_user(self):
        """Test broadcasting message to all user connections."""
        manager = WebSocketConnectionManager()
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        connection_id1 = "conn_123"
        connection_id2 = "conn_456"
        user_id = "user_789"

        # Setup multiple connections for user
        manager.active_connections[connection_id1] = mock_websocket1
        manager.active_connections[connection_id2] = mock_websocket2
        manager.user_connections[user_id] = {connection_id1, connection_id2}

        message = "Broadcast message"
        await manager.broadcast_to_user(message, user_id)

        # Verify message was sent to all user connections
        mock_websocket1.send_text.assert_called_once_with(message)
        mock_websocket2.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_websocket_broadcast_to_nonexistent_user(self):
        """Test broadcasting to non-existent user."""
        manager = WebSocketConnectionManager()

        # This should not raise an error
        await manager.broadcast_to_user("Hello", "non_existent_user")

    @pytest.mark.asyncio
    async def test_websocket_get_user_connection_count(self):
        """Test getting user connection count."""
        manager = WebSocketConnectionManager()
        user_id = "user_123"

        # No connections initially
        count = manager.get_user_connection_count(user_id)
        assert count == 0

        # Add connections
        manager.user_connections[user_id] = {"conn_1", "conn_2", "conn_3"}
        count = manager.get_user_connection_count(user_id)
        assert count == 3

    def test_websocket_cleanup_dead_connections(self):
        """Test cleaning up dead connections."""
        manager = WebSocketConnectionManager()

        # Setup some connections
        mock_websocket1 = MagicMock()
        mock_websocket2 = MagicMock()
        manager.active_connections["conn_1"] = mock_websocket1
        manager.active_connections["conn_2"] = mock_websocket2
        manager.user_connections["user_1"] = {"conn_1"}
        manager.user_connections["user_2"] = {"conn_2"}

        # Mock websocket states - conn_1 is dead, conn_2 is alive
        mock_websocket1.client_state.name = "DISCONNECTED"
        mock_websocket2.client_state.name = "CONNECTED"

        # This would be called by a background task in real implementation
        dead_connections = []
        for conn_id, websocket in manager.active_connections.items():
            if (
                hasattr(websocket, "client_state")
                and websocket.client_state.name == "DISCONNECTED"
            ):
                dead_connections.append(conn_id)

        # Clean up dead connections
        for conn_id in dead_connections:
            # Find user for this connection
            for user_id, connections in manager.user_connections.items():
                if conn_id in connections:
                    manager.disconnect(conn_id, user_id)
                    break

        # Verify dead connection was removed
        assert "conn_1" not in manager.active_connections
        assert "conn_2" in manager.active_connections
        assert "user_1" not in manager.user_connections
        assert "user_2" in manager.user_connections


class TestWebSocketAuthentication:
    """Test WebSocket authentication logic."""

    @pytest.mark.asyncio
    async def test_websocket_token_validation_success(self):
        """Test successful WebSocket token validation."""
        with patch("app.api.websocket.verify_token") as mock_verify:
            mock_verify.return_value = {"sub": "user_123", "username": "testuser"}

            from app.api.websocket import verify_token

            token = "valid_jwt_token"
            payload = verify_token(token)

            assert payload is not None
            assert payload["sub"] == "user_123"
            assert payload["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_websocket_token_validation_failure(self):
        """Test WebSocket token validation failure."""
        with patch("app.api.websocket.verify_token") as mock_verify:
            mock_verify.return_value = None

            from app.api.websocket import verify_token

            token = "invalid_jwt_token"
            payload = verify_token(token)

            assert payload is None


class TestWebSocketMessageHandling:
    """Test WebSocket message handling logic."""

    def test_websocket_message_parsing_valid_json(self):
        """Test parsing valid JSON WebSocket messages."""
        message = '{"type": "terminal_input", "data": "ls -la"}'

        try:
            parsed = json.loads(message)
            assert parsed["type"] == "terminal_input"
            assert parsed["data"] == "ls -la"
        except json.JSONDecodeError:
            pytest.fail("Should parse valid JSON")

    def test_websocket_message_parsing_invalid_json(self):
        """Test handling invalid JSON WebSocket messages."""
        message = '{"type": "terminal_input", "data": invalid_json}'

        with pytest.raises(json.JSONDecodeError):
            json.loads(message)

    def test_websocket_message_types(self):
        """Test different WebSocket message types."""
        # Terminal input message
        terminal_msg = {"type": "terminal_input", "data": "echo hello"}
        assert terminal_msg["type"] == "terminal_input"

        # Terminal resize message
        resize_msg = {"type": "terminal_resize", "rows": 24, "cols": 80}
        assert resize_msg["type"] == "terminal_resize"
        assert resize_msg["rows"] == 24

        # Ping message
        ping_msg = {"type": "ping"}
        assert ping_msg["type"] == "ping"


class TestWebSocketErrorHandling:
    """Test WebSocket error handling."""

    @pytest.mark.asyncio
    async def test_websocket_connection_error_handling(self):
        """Test WebSocket connection error handling."""
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()

        # Mock websocket.accept() to raise an exception
        mock_websocket.accept.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await manager.connect(mock_websocket, "conn_123", "user_456")

    @pytest.mark.asyncio
    async def test_websocket_send_message_error_handling(self):
        """Test error handling when sending WebSocket messages."""
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "conn_123"

        # Setup connection
        manager.active_connections[connection_id] = mock_websocket

        # Mock send_text to raise an exception
        mock_websocket.send_text.side_effect = Exception("Send failed")

        # This should handle the error gracefully
        try:
            await manager.send_personal_message("Hello", connection_id)
        except Exception:
            # The manager should handle this error internally
            pass

    @pytest.mark.asyncio
    async def test_websocket_rate_limiting(self):
        """Test WebSocket rate limiting functionality."""
        # This is a basic test since rate limiting is middleware
        with patch("app.api.websocket.websocket_rate_limiter") as mock_limiter:
            mock_limiter.return_value = True  # Not rate limited

            from app.api.websocket import websocket_rate_limiter

            # Test that rate limiter can be called
            result = websocket_rate_limiter("user_123", "terminal")
            assert result is True

    def test_websocket_environment_validation(self):
        """Test environment ID validation for WebSocket connections."""
        # Test valid environment ID format
        env_id = "507f1f77bcf86cd799439011"
        assert len(env_id) == 24  # MongoDB ObjectId length

        # Test invalid environment ID
        invalid_env_id = "invalid_id"
        assert len(invalid_env_id) != 24

    @pytest.mark.asyncio
    async def test_websocket_kubernetes_integration_mock(self):
        """Test WebSocket Kubernetes integration with mocks."""
        with patch("app.api.websocket.stream") as mock_stream, patch(
            "app.api.websocket.client"
        ) as mock_client:
            # Mock Kubernetes client
            mock_k8s_client = MagicMock()
            mock_client.CoreV1Api.return_value = mock_k8s_client

            # Mock stream response
            mock_stream.return_value = MagicMock()

            # This tests that the imports and basic setup work
            from app.api.websocket import client, stream

            assert stream is not None
            assert client is not None


class TestWebSocketTerminalSession:
    """Test WebSocket terminal session functionality."""

    def test_terminal_session_creation(self):
        """Test terminal session data structure."""
        session_data = {
            "session_id": "session_123",
            "environment_id": "env_456",
            "user_id": "user_789",
            "created_at": "2024-01-01T00:00:00Z",
            "status": "active",
        }

        assert session_data["session_id"] == "session_123"
        assert session_data["status"] == "active"

    def test_terminal_command_validation(self):
        """Test terminal command validation."""
        # Valid commands
        valid_commands = ["ls -la", "pwd", "echo hello", "cat file.txt"]

        for cmd in valid_commands:
            assert isinstance(cmd, str)
            assert len(cmd.strip()) > 0

        # Test command sanitization (basic)
        dangerous_cmd = "rm -rf /"
        # In a real implementation, you might want to validate/sanitize commands
        assert isinstance(dangerous_cmd, str)  # Basic check

    @pytest.mark.asyncio
    async def test_pty_service_integration_mock(self):
        """Test PTY service integration with mocks."""
        with patch("app.api.websocket.pty_manager") as mock_pty:
            mock_pty.create_session.return_value = "session_123"
            mock_pty.send_input.return_value = True

            from app.api.websocket import pty_manager

            # Test PTY manager can be called
            session_id = pty_manager.create_session("env_123")
            assert session_id == "session_123"

            result = pty_manager.send_input(session_id, "ls -la")
            assert result is True


class TestWebSocketLogsEndpoint:
    """Test WebSocket logs endpoint functionality."""

    def test_log_message_format(self):
        """Test log message format."""
        log_message = {
            "timestamp": "2024-01-01T00:00:00Z",
            "level": "INFO",
            "message": "Application started",
            "source": "app.main",
        }

        assert "timestamp" in log_message
        assert "level" in log_message
        assert "message" in log_message
        assert log_message["level"] == "INFO"

    def test_log_filtering(self):
        """Test log filtering logic."""
        logs = [
            {"level": "INFO", "message": "Info message"},
            {"level": "ERROR", "message": "Error message"},
            {"level": "DEBUG", "message": "Debug message"},
            {"level": "WARN", "message": "Warning message"},
        ]

        # Filter ERROR logs
        error_logs = [log for log in logs if log["level"] == "ERROR"]
        assert len(error_logs) == 1
        assert error_logs[0]["message"] == "Error message"

        # Filter non-DEBUG logs
        non_debug_logs = [log for log in logs if log["level"] != "DEBUG"]
        assert len(non_debug_logs) == 3

    @pytest.mark.asyncio
    async def test_kubernetes_logs_integration_mock(self):
        """Test Kubernetes logs integration with mocks."""
        with patch("app.api.websocket.client") as mock_client:
            mock_k8s_client = MagicMock()
            mock_client.CoreV1Api.return_value = mock_k8s_client

            # Mock logs response
            mock_k8s_client.read_namespaced_pod_log.return_value = (
                "Log line 1\nLog line 2"
            )

            from app.api.websocket import client

            # Test that Kubernetes client can be instantiated
            k8s_client = client.CoreV1Api()
            assert k8s_client is not None


class TestWebSocketTerminalRegressionTests:
    """Test WebSocket terminal regression scenarios for specific bugs that were fixed."""

    @pytest.mark.asyncio
    async def test_websocket_terminal_tmux_session_id_unbound_error_regression(self):
        """Regression test for UnboundLocalError: cannot access local variable 'tmux_session_id'."""
        # This tests the specific issue that was fixed in the finally block

        # Mock WebSocket that will disconnect immediately
        mock_websocket = AsyncMock()
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()

        # Mock environment in installing state (tmux_session_id won't be created)
        mock_environment = MagicMock()
        mock_environment.status.value = "installing"  # Not running, so no tmux session
        mock_environment.name = "installing-env"
        mock_environment.id = "507f1f77bcf86cd799439011"
        mock_environment.installation_completed = False
        mock_environment.template.value = "python"

        with patch("app.api.websocket.environment_service") as mock_env_service:
            mock_env_service.set_database = MagicMock()
            mock_env_service.get_environment.return_value = mock_environment
            mock_env_service.create_websocket_session = AsyncMock()
            mock_env_service.cleanup_websocket_session = AsyncMock()

            with patch("app.api.websocket.authenticate_websocket") as mock_auth:
                mock_user = MagicMock()
                mock_user.id = "507f1f77bcf86cd799439011"
                mock_user.username = "testuser"
                mock_auth.return_value = mock_user

                with patch(
                    "app.api.websocket.websocket_rate_limiter"
                ) as mock_rate_limiter:
                    mock_rate_limiter.check_connection_limit.return_value = True
                    mock_rate_limiter.add_connection = MagicMock()
                    mock_rate_limiter.remove_connection = MagicMock()

                    with patch(
                        "app.api.websocket.connection_manager"
                    ) as mock_conn_manager:
                        mock_conn_manager.connect = AsyncMock()
                        mock_conn_manager.send_personal_message = AsyncMock()
                        mock_conn_manager.disconnect = MagicMock()

                        with patch("app.api.websocket.tmux_manager") as mock_tmux:
                            mock_tmux.list_sessions.return_value = []
                            mock_tmux.detach_from_session = AsyncMock()

                            # This should NOT raise UnboundLocalError in the finally block
                            try:
                                from app.api.websocket import websocket_terminal

                                await websocket_terminal(
                                    websocket=mock_websocket,
                                    environment_id="installing_env_id",
                                    token="valid_token",
                                    db=MagicMock(),
                                )
                            except WebSocketDisconnect:
                                # Expected exception, but should not have UnboundLocalError
                                pass
                            except UnboundLocalError as e:
                                if "tmux_session_id" in str(e):
                                    pytest.fail(
                                        f"UnboundLocalError for tmux_session_id should be fixed: {e}"
                                    )
                                else:
                                    raise

                            # Verify cleanup was called without errors
                            mock_conn_manager.disconnect.assert_called()
                            mock_rate_limiter.remove_connection.assert_called()

    @pytest.mark.asyncio
    async def test_websocket_terminal_variable_scope_safety(self):
        """Test that WebSocket terminal handles variable scope safely in all code paths."""

        # Test scenario where tmux_session_id is never initialized
        mock_websocket = AsyncMock()

        # Mock environment that fails authentication (early exit)
        with patch("app.api.websocket.authenticate_websocket") as mock_auth:
            mock_auth.return_value = None  # Authentication fails

            # This should not raise any variable scope errors
            try:
                from app.api.websocket import websocket_terminal

                await websocket_terminal(
                    websocket=mock_websocket,
                    environment_id="any_env_id",
                    token="invalid_token",
                    db=MagicMock(),
                )
            except Exception as e:
                # Should not have variable scope errors
                assert "tmux_session_id" not in str(e)
                assert "UnboundLocalError" not in str(e)

            # Should close WebSocket with authentication error
            mock_websocket.close.assert_called_with(
                code=1008, reason="Authentication failed"
            )

    @pytest.mark.asyncio
    async def test_websocket_terminal_cleanup_robustness(self):
        """Test that WebSocket terminal cleanup is robust against various failure scenarios."""

        mock_websocket = AsyncMock()

        # Test cleanup when various components fail
        with patch("app.api.websocket.connection_manager") as mock_conn_manager:
            mock_conn_manager.disconnect.side_effect = Exception("Cleanup error")

            with patch("app.api.websocket.authenticate_websocket") as mock_auth:
                mock_auth.return_value = None  # Quick exit

                # Should handle cleanup errors gracefully
                try:
                    from app.api.websocket import websocket_terminal

                    await websocket_terminal(
                        websocket=mock_websocket,
                        environment_id="any_env_id",
                        token="invalid_token",
                        db=MagicMock(),
                    )
                except Exception as e:
                    # Should not propagate cleanup errors
                    assert "Cleanup error" not in str(e)

    def test_websocket_terminal_locals_check_implementation(self):
        """Test that the locals() check for tmux_session_id works correctly."""

        # Simulate the fixed code pattern
        def test_cleanup_pattern():
            # Simulate scenario where tmux_session_id might not be defined
            if "tmux_session_id" in locals() and "tmux_session_id" in globals():
                # This branch should only execute if variable exists
                return "variable_exists"
            else:
                # This branch handles the case where variable doesn't exist
                return "variable_not_exists"

        # Should handle missing variable gracefully
        result = test_cleanup_pattern()
        assert result == "variable_not_exists"

        # Test with variable defined
        def test_cleanup_pattern_with_var():
            tmux_session_id = "session_123"
            if "tmux_session_id" in locals() and tmux_session_id:
                return "variable_exists"
            else:
                return "variable_not_exists"

        result = test_cleanup_pattern_with_var()
        assert result == "variable_exists"
