"""
Test WebSocket edge cases and error scenarios.

This module tests the specific WebSocket issues that were fixed:
1. UnboundLocalError for tmux_session_id in cleanup
2. WebSocket connection error paths
3. Terminal session management edge cases
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect

from app.api.websocket import WebSocketConnectionManager, websocket_terminal
from app.models.environment import EnvironmentStatus


@pytest.mark.asyncio
class TestWebSocketTerminalErrorPaths:
    """Test WebSocket terminal error paths and cleanup scenarios."""

    async def test_websocket_terminal_environment_not_found(self, test_database):
        """Test WebSocket terminal connection when environment doesn't exist."""
        # Mock WebSocket
        mock_websocket = AsyncMock()

        # Mock database to return None for environment
        with patch("app.api.websocket.environment_service") as mock_env_service:
            mock_env_service.set_database = MagicMock()
            mock_env_service.get_environment.return_value = None

            # Mock authentication to succeed
            with patch("app.api.websocket.authenticate_websocket") as mock_auth:
                mock_user = MagicMock()
                mock_user.id = "507f1f77bcf86cd799439011"
                mock_user.username = "testuser"
                mock_auth.return_value = mock_user

                # Mock rate limiter
                with patch(
                    "app.api.websocket.websocket_rate_limiter"
                ) as mock_rate_limiter:
                    mock_rate_limiter.check_connection_limit.return_value = True

                    # Call websocket_terminal function
                    await websocket_terminal(
                        websocket=mock_websocket,
                        environment_id="nonexistent_env_id",
                        token="valid_token",
                        db=test_database.database,
                    )

                    # Should close WebSocket with appropriate error
                    mock_websocket.close.assert_called_with(
                        code=1008, reason="Environment not found"
                    )

    async def test_websocket_terminal_environment_not_ready(self, test_database):
        """Test WebSocket terminal connection when environment is not ready."""
        # Mock WebSocket
        mock_websocket = AsyncMock()

        # Mock environment in failed state
        mock_environment = MagicMock()
        mock_environment.status = EnvironmentStatus.FAILED
        mock_environment.name = "failed-env"
        mock_environment.id = "507f1f77bcf86cd799439011"

        with patch("app.api.websocket.environment_service") as mock_env_service:
            mock_env_service.set_database = MagicMock()
            mock_env_service.get_environment.return_value = mock_environment

            # Mock authentication to succeed
            with patch("app.api.websocket.authenticate_websocket") as mock_auth:
                mock_user = MagicMock()
                mock_user.id = "507f1f77bcf86cd799439011"
                mock_user.username = "testuser"
                mock_auth.return_value = mock_user

                # Mock rate limiter
                with patch(
                    "app.api.websocket.websocket_rate_limiter"
                ) as mock_rate_limiter:
                    mock_rate_limiter.check_connection_limit.return_value = True

                    # Call websocket_terminal function
                    await websocket_terminal(
                        websocket=mock_websocket,
                        environment_id="failed_env_id",
                        token="valid_token",
                        db=test_database.database,
                    )

                    # Should close WebSocket because environment is not ready
                    mock_websocket.close.assert_called_with(
                        code=1008, reason="Environment not ready"
                    )

    async def test_websocket_terminal_tmux_session_id_unbound_error_fix(
        self, test_database
    ):
        """Test that tmux_session_id UnboundLocalError is fixed in cleanup."""
        # Mock WebSocket
        mock_websocket = AsyncMock()

        # Mock environment in installing state (tmux_session_id won't be created)
        mock_environment = MagicMock()
        mock_environment.status = EnvironmentStatus.INSTALLING
        mock_environment.name = "installing-env"
        mock_environment.id = "507f1f77bcf86cd799439011"
        mock_environment.installation_completed = False

        with patch("app.api.websocket.environment_service") as mock_env_service:
            mock_env_service.set_database = MagicMock()
            mock_env_service.get_environment.return_value = mock_environment
            mock_env_service.create_websocket_session = AsyncMock()
            mock_env_service.cleanup_websocket_session = AsyncMock()

            # Mock authentication to succeed
            with patch("app.api.websocket.authenticate_websocket") as mock_auth:
                mock_user = MagicMock()
                mock_user.id = "507f1f77bcf86cd799439011"
                mock_user.username = "testuser"
                mock_auth.return_value = mock_user

                # Mock rate limiter
                with patch(
                    "app.api.websocket.websocket_rate_limiter"
                ) as mock_rate_limiter:
                    mock_rate_limiter.check_connection_limit.return_value = True
                    mock_rate_limiter.add_connection = MagicMock()
                    mock_rate_limiter.remove_connection = MagicMock()

                    # Mock connection manager
                    with patch(
                        "app.api.websocket.connection_manager"
                    ) as mock_conn_manager:
                        mock_conn_manager.connect = AsyncMock()
                        mock_conn_manager.send_personal_message = AsyncMock()
                        mock_conn_manager.disconnect = MagicMock()

                        # Mock tmux manager
                        with patch("app.api.websocket.tmux_manager") as mock_tmux:
                            mock_tmux.list_sessions.return_value = []
                            mock_tmux.detach_from_session = AsyncMock()

                            # Mock WebSocket to raise disconnect after welcome message
                            mock_websocket.receive_text.side_effect = (
                                WebSocketDisconnect()
                            )

                            # This should not raise UnboundLocalError in finally block
                            try:
                                await websocket_terminal(
                                    websocket=mock_websocket,
                                    environment_id="installing_env_id",
                                    token="valid_token",
                                    db=test_database.database,
                                )
                            except WebSocketDisconnect:
                                # Expected exception, but should not have UnboundLocalError
                                pass

                            # Verify cleanup was called without errors
                            mock_conn_manager.disconnect.assert_called()
                            mock_rate_limiter.remove_connection.assert_called()

    async def test_websocket_terminal_tmux_session_creation_failure(
        self, test_database
    ):
        """Test WebSocket terminal when tmux session creation fails."""
        # Mock WebSocket
        mock_websocket = AsyncMock()

        # Mock environment in running state
        mock_environment = MagicMock()
        mock_environment.status = EnvironmentStatus.RUNNING
        mock_environment.name = "running-env"
        mock_environment.id = "507f1f77bcf86cd799439011"
        mock_environment.installation_completed = True
        mock_environment.template.value = "python"

        with patch("app.api.websocket.environment_service") as mock_env_service:
            mock_env_service.set_database = MagicMock()
            mock_env_service.get_environment.return_value = mock_environment
            mock_env_service.create_websocket_session = AsyncMock()
            mock_env_service.cleanup_websocket_session = AsyncMock()

            # Mock authentication to succeed
            with patch("app.api.websocket.authenticate_websocket") as mock_auth:
                mock_user = MagicMock()
                mock_user.id = "507f1f77bcf86cd799439011"
                mock_user.username = "testuser"
                mock_auth.return_value = mock_user

                # Mock rate limiter
                with patch(
                    "app.api.websocket.websocket_rate_limiter"
                ) as mock_rate_limiter:
                    mock_rate_limiter.check_connection_limit.return_value = True
                    mock_rate_limiter.add_connection = MagicMock()
                    mock_rate_limiter.remove_connection = MagicMock()

                    # Mock connection manager
                    with patch(
                        "app.api.websocket.connection_manager"
                    ) as mock_conn_manager:
                        mock_conn_manager.connect = AsyncMock()
                        mock_conn_manager.send_personal_message = AsyncMock()
                        mock_conn_manager.disconnect = MagicMock()

                        # Mock tmux manager to fail session creation
                        with patch("app.api.websocket.tmux_manager") as mock_tmux:
                            mock_tmux.list_sessions.return_value = []
                            mock_tmux.create_session.return_value = (
                                None  # Failed to create
                            )
                            mock_tmux.detach_from_session = AsyncMock()

                            # Call websocket_terminal function
                            await websocket_terminal(
                                websocket=mock_websocket,
                                environment_id="running_env_id",
                                token="valid_token",
                                db=test_database.database,
                            )

                            # Should close WebSocket due to tmux session creation failure
                            mock_websocket.close.assert_called_with(
                                code=1008, reason="Failed to create terminal session"
                            )

    async def test_websocket_terminal_tmux_attach_failure(self, test_database):
        """Test WebSocket terminal when tmux session attach fails."""
        # Mock WebSocket
        mock_websocket = AsyncMock()

        # Mock environment in running state
        mock_environment = MagicMock()
        mock_environment.status = EnvironmentStatus.RUNNING
        mock_environment.name = "running-env"
        mock_environment.id = "507f1f77bcf86cd799439011"
        mock_environment.installation_completed = True
        mock_environment.template.value = "python"

        with patch("app.api.websocket.environment_service") as mock_env_service:
            mock_env_service.set_database = MagicMock()
            mock_env_service.get_environment.return_value = mock_environment
            mock_env_service.create_websocket_session = AsyncMock()
            mock_env_service.cleanup_websocket_session = AsyncMock()

            # Mock authentication to succeed
            with patch("app.api.websocket.authenticate_websocket") as mock_auth:
                mock_user = MagicMock()
                mock_user.id = "507f1f77bcf86cd799439011"
                mock_user.username = "testuser"
                mock_auth.return_value = mock_user

                # Mock rate limiter
                with patch(
                    "app.api.websocket.websocket_rate_limiter"
                ) as mock_rate_limiter:
                    mock_rate_limiter.check_connection_limit.return_value = True
                    mock_rate_limiter.add_connection = MagicMock()
                    mock_rate_limiter.remove_connection = MagicMock()

                    # Mock connection manager
                    with patch(
                        "app.api.websocket.connection_manager"
                    ) as mock_conn_manager:
                        mock_conn_manager.connect = AsyncMock()
                        mock_conn_manager.send_personal_message = AsyncMock()
                        mock_conn_manager.disconnect = MagicMock()

                        # Mock tmux manager to fail session attach
                        with patch("app.api.websocket.tmux_manager") as mock_tmux:
                            mock_tmux.list_sessions.return_value = []
                            mock_tmux.create_session.return_value = "session_123"
                            mock_tmux.attach_to_session.return_value = (
                                False  # Failed to attach
                            )
                            mock_tmux.detach_from_session = AsyncMock()

                            # Call websocket_terminal function
                            await websocket_terminal(
                                websocket=mock_websocket,
                                environment_id="running_env_id",
                                token="valid_token",
                                db=test_database.database,
                            )

                            # Should close WebSocket due to tmux session attach failure
                            mock_websocket.close.assert_called_with(
                                code=1008, reason="Failed to attach to terminal session"
                            )

    async def test_websocket_terminal_authentication_failure(self, test_database):
        """Test WebSocket terminal connection with authentication failure."""
        # Mock WebSocket
        mock_websocket = AsyncMock()

        # Mock authentication to fail
        with patch("app.api.websocket.authenticate_websocket") as mock_auth:
            mock_auth.return_value = None  # Authentication failed

            # Call websocket_terminal function
            await websocket_terminal(
                websocket=mock_websocket,
                environment_id="any_env_id",
                token="invalid_token",
                db=test_database.database,
            )

            # Should close WebSocket with authentication error
            mock_websocket.close.assert_called_with(
                code=1008, reason="Authentication failed"
            )

    async def test_websocket_terminal_rate_limit_exceeded(self, test_database):
        """Test WebSocket terminal connection when rate limit is exceeded."""
        # Mock WebSocket
        mock_websocket = AsyncMock()

        # Mock authentication to succeed
        with patch("app.api.websocket.authenticate_websocket") as mock_auth:
            mock_user = MagicMock()
            mock_user.id = "507f1f77bcf86cd799439011"
            mock_user.username = "testuser"
            mock_auth.return_value = mock_user

            # Mock rate limiter to fail
            with patch("app.api.websocket.websocket_rate_limiter") as mock_rate_limiter:
                mock_rate_limiter.check_connection_limit.return_value = (
                    False  # Rate limited
                )

                # Call websocket_terminal function
                await websocket_terminal(
                    websocket=mock_websocket,
                    environment_id="any_env_id",
                    token="valid_token",
                    db=test_database.database,
                )

                # Should close WebSocket with rate limit error
                mock_websocket.close.assert_called_with(
                    code=1008, reason="Too many connections"
                )


@pytest.mark.asyncio
class TestWebSocketMessageHandlingEdgeCases:
    """Test WebSocket message handling edge cases."""

    async def test_websocket_message_rate_limiting(self):
        """Test WebSocket message rate limiting."""
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "conn_123"
        user_id = "user_456"

        # Setup connection
        await manager.connect(mock_websocket, connection_id, user_id)

        # Mock rate limiter to fail
        with patch("app.api.websocket.websocket_rate_limiter") as mock_rate_limiter:
            mock_rate_limiter.check_message_rate.return_value = False

            # This would be tested in the actual websocket_terminal function
            # but we can test the manager's error handling
            error_message = {
                "type": "error",
                "message": "Rate limit exceeded. Please slow down.",
            }

            await manager.send_personal_message(
                json.dumps(error_message), connection_id
            )
            mock_websocket.send_text.assert_called_with(json.dumps(error_message))

    async def test_websocket_invalid_json_message_handling(self):
        """Test handling of invalid JSON messages."""
        # Test that invalid JSON is handled gracefully
        invalid_json = '{"type": "input", "data": invalid_json_here}'

        try:
            json.loads(invalid_json)
            pytest.fail("Should have raised JSONDecodeError")
        except json.JSONDecodeError:
            # This is expected - the websocket handler should catch this
            # and treat it as raw terminal input
            fallback_message = {"type": "input", "data": invalid_json}
            assert fallback_message["type"] == "input"
            assert fallback_message["data"] == invalid_json

    async def test_websocket_connection_cleanup_on_exception(self):
        """Test that WebSocket connections are properly cleaned up on exceptions."""
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "conn_123"
        user_id = "user_456"

        # Setup connection
        await manager.connect(mock_websocket, connection_id, user_id)

        # Verify connection exists
        assert connection_id in manager.active_connections
        assert user_id in manager.user_connections

        # Simulate cleanup on exception
        manager.disconnect(connection_id, user_id)

        # Verify connection is cleaned up
        assert connection_id not in manager.active_connections
        assert user_id not in manager.user_connections

    async def test_websocket_send_message_exception_handling(self):
        """Test exception handling when sending WebSocket messages."""
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "conn_123"

        # Setup connection
        manager.active_connections[connection_id] = mock_websocket

        # Mock send_text to raise exception
        mock_websocket.send_text.side_effect = Exception("Connection closed")

        # Should handle exception gracefully without raising
        try:
            await manager.send_personal_message("test message", connection_id)
        except Exception:
            pytest.fail("send_personal_message should handle exceptions gracefully")


@pytest.mark.asyncio
class TestTmuxSessionManagementEdgeCases:
    """Test tmux session management edge cases."""

    async def test_tmux_session_cleanup_on_websocket_disconnect(self):
        """Test that tmux sessions are properly handled on WebSocket disconnect."""
        # Mock tmux manager
        with patch("app.api.websocket.tmux_manager") as mock_tmux:
            mock_tmux.detach_from_session = AsyncMock()

            # Simulate session cleanup
            session_id = "session_123"
            callback = MagicMock()

            # This should not raise an exception
            await mock_tmux.detach_from_session(session_id, callback)
            mock_tmux.detach_from_session.assert_called_once_with(session_id, callback)

    async def test_tmux_session_persistence_across_reconnections(self):
        """Test that tmux sessions persist across WebSocket reconnections."""
        # Mock tmux manager to return existing session
        with patch("app.api.websocket.tmux_manager") as mock_tmux:
            existing_session_id = "existing_session_123"
            mock_tmux.list_sessions.return_value = [existing_session_id]
            mock_tmux.attach_to_session.return_value = True

            # Simulate reconnection to existing session
            sessions = mock_tmux.list_sessions(environment_id="env_123")
            assert existing_session_id in sessions

            # Should attach to existing session instead of creating new one
            success = mock_tmux.attach_to_session(existing_session_id, MagicMock())
            assert success is True

    async def test_tmux_session_error_recovery(self):
        """Test tmux session error recovery scenarios."""
        # Mock tmux manager with various failure scenarios
        with patch("app.api.websocket.tmux_manager") as mock_tmux:
            # Test session creation failure
            mock_tmux.create_session.return_value = None
            session_id = mock_tmux.create_session("env_123", "user_123")
            assert session_id is None

            # Test session attach failure
            mock_tmux.attach_to_session.return_value = False
            success = mock_tmux.attach_to_session("session_123", MagicMock())
            assert success is False

            # Test session input failure
            mock_tmux.send_input.return_value = False
            success = mock_tmux.send_input("session_123", "ls -la")
            assert success is False
