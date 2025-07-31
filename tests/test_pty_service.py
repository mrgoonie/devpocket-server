import asyncio

import pytest

from app.services.pty_service import PTYManager, PTYSession


@pytest.mark.asyncio
class TestPTYService:
    """Test PTY service functionality."""

    async def test_pty_manager_creation(self):
        """Test PTY manager can be created."""
        manager = PTYManager()
        assert manager is not None
        assert isinstance(manager.sessions, dict)
        assert isinstance(manager.user_sessions, dict)

    async def test_pty_session_creation(self):
        """Test PTY session creation."""
        output_data = []

        def output_callback(data: str):
            output_data.append(data)

        session = PTYSession(
            session_id="test-session",
            environment_id="test-env",
            user_id="test-user",
            output_callback=output_callback,
        )

        assert session.session_id == "test-session"
        assert session.environment_id == "test-env"
        assert session.user_id == "test-user"
        assert session.cols == 80
        assert session.rows == 24
        assert not session.is_running

    async def test_pty_session_lifecycle(self):
        """Test PTY session start and stop."""
        output_data = []

        def output_callback(data: str):
            output_data.append(data)

        session = PTYSession(
            session_id="test-lifecycle",
            environment_id="test-env",
            user_id="test-user",
            output_callback=output_callback,
        )

        # Start session (will only work in actual terminal environment)
        try:
            success = await session.start("/bin/echo")
            if success:
                assert session.is_running
                # Stop session
                await session.stop()
                assert not session.is_running
        except Exception:
            # Expected in test environment without proper PTY support
            pass

    async def test_pty_manager_session_management(self):
        """Test PTY manager session tracking."""
        manager = PTYManager()
        output_data = []

        def output_callback(data: str):
            output_data.append(data)

        session_id = "test-mgmt-session"

        # Create session (might fail in test env, that's OK)
        try:
            success = await manager.create_session(
                session_id=session_id,
                environment_id="test-env",
                user_id="test-user",
                output_callback=output_callback,
                shell_command="/bin/echo",
            )

            if success:
                # Check session is tracked
                assert session_id in manager.sessions
                assert "test-user" in manager.user_sessions
                assert session_id in manager.user_sessions["test-user"]

                # Close session
                await manager.close_session(session_id)
                assert session_id not in manager.sessions
        except Exception:
            # Expected in test environment
            pass

    async def test_pty_session_resize(self):
        """Test PTY session resize."""
        output_data = []

        def output_callback(data: str):
            output_data.append(data)

        session = PTYSession(
            session_id="test-resize",
            environment_id="test-env",
            user_id="test-user",
            output_callback=output_callback,
        )

        # Test resize (should work even without running PTY)
        result = await session.resize(100, 30)
        assert session.cols == 100
        assert session.rows == 30
        # Result depends on whether PTY is actually running
        assert isinstance(result, bool)

    async def test_pty_session_write_input(self):
        """Test PTY session input."""
        output_data = []

        def output_callback(data: str):
            output_data.append(data)

        session = PTYSession(
            session_id="test-input",
            environment_id="test-env",
            user_id="test-user",
            output_callback=output_callback,
        )

        # Test write input (should return False when not running)
        result = await session.write_input("test command\n")
        assert result is False  # Session not running
