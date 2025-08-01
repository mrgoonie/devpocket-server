"""
Tmux Session Management Service

This service manages tmux sessions for persistent terminal access in development environments.
It provides session lifecycle management, including creation, attachment, detachment, and cleanup.
"""

import asyncio
import json
import os
import uuid
from typing import Callable, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class TmuxSession:
    """Represents a tmux session with its metadata and state"""

    def __init__(self, session_id: str, environment_id: str, user_id: str):
        self.session_id = session_id
        self.environment_id = environment_id
        self.user_id = user_id
        self.created_at = asyncio.get_event_loop().time()
        self.last_activity = self.created_at
        self.is_active = False
        self.output_callbacks: List[Callable[[str], None]] = []

    def add_output_callback(self, callback: Callable[[str], None]):
        """Add callback for session output"""
        self.output_callbacks.append(callback)

    def remove_output_callback(self, callback: Callable[[str], None]):
        """Remove output callback"""
        if callback in self.output_callbacks:
            self.output_callbacks.remove(callback)

    async def send_output(self, data: str):
        """Send output to all registered callbacks"""
        for callback in self.output_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Error in output callback: {e}")


class TmuxSessionManager:
    """Manages tmux sessions for development environments"""

    def __init__(self):
        self.sessions: Dict[str, TmuxSession] = {}
        self.user_sessions: Dict[str, set] = {}  # user_id -> set of session_ids
        self.environment_sessions: Dict[
            str, set
        ] = {}  # environment_id -> set of session_ids

    async def create_session(
        self,
        environment_id: str,
        user_id: str,
        session_name: Optional[str] = None,
        initial_command: Optional[str] = None,
    ) -> Optional[str]:
        """Create a new tmux session"""
        try:
            session_id = (
                session_name or f"devpocket_{environment_id}_{uuid.uuid4().hex[:8]}"
            )

            # Check if session already exists
            if await self._session_exists(session_id):
                logger.warning(f"Tmux session {session_id} already exists")
                return None

            # Create tmux session in detached mode
            cmd = f"tmux new-session -d -s {session_id}"
            if initial_command:
                cmd += f" '{initial_command}'"

            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(
                    f"Failed to create tmux session {session_id}: {stderr.decode()}"
                )
                return None

            # Create session object
            session = TmuxSession(session_id, environment_id, user_id)
            session.is_active = True

            # Track session
            self.sessions[session_id] = session

            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)

            if environment_id not in self.environment_sessions:
                self.environment_sessions[environment_id] = set()
            self.environment_sessions[environment_id].add(session_id)

            logger.info(
                f"Created tmux session {session_id} for user {user_id} in environment {environment_id}"
            )
            return session_id

        except Exception as e:
            logger.error(f"Error creating tmux session: {e}")
            return None

    async def attach_to_session(
        self, session_id: str, output_callback: Callable[[str], None]
    ) -> bool:
        """Attach to an existing tmux session"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False

            # Check if tmux session still exists
            if not await self._session_exists(session_id):
                logger.error(f"Tmux session {session_id} no longer exists")
                await self._cleanup_session(session_id)
                return False

            # Add output callback
            session.add_output_callback(output_callback)
            session.last_activity = asyncio.get_event_loop().time()

            logger.info(f"Attached to tmux session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error attaching to tmux session {session_id}: {e}")
            return False

    async def detach_from_session(
        self, session_id: str, output_callback: Callable[[str], None]
    ):
        """Detach from a tmux session"""
        try:
            session = self.sessions.get(session_id)
            if session:
                session.remove_output_callback(output_callback)
                logger.info(f"Detached from tmux session {session_id}")

        except Exception as e:
            logger.error(f"Error detaching from tmux session {session_id}: {e}")

    async def send_input(self, session_id: str, data: str) -> bool:
        """Send input to a tmux session"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False

            # Check if tmux session still exists
            if not await self._session_exists(session_id):
                logger.error(f"Tmux session {session_id} no longer exists")
                await self._cleanup_session(session_id)
                return False

            # Send input to tmux session
            cmd = f"tmux send-keys -t {session_id} {repr(data)}"
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(
                    f"Failed to send input to tmux session {session_id}: {stderr.decode()}"
                )
                return False

            session.last_activity = asyncio.get_event_loop().time()
            return True

        except Exception as e:
            logger.error(f"Error sending input to tmux session {session_id}: {e}")
            return False

    async def resize_session(self, session_id: str, cols: int, rows: int) -> bool:
        """Resize a tmux session"""
        try:
            session = self.sessions.get(session_id)
            if not session:
                logger.error(f"Session {session_id} not found")
                return False

            # Check if tmux session still exists
            if not await self._session_exists(session_id):
                logger.error(f"Tmux session {session_id} no longer exists")
                await self._cleanup_session(session_id)
                return False

            # Resize tmux window (sessions don't have a resize command, windows do)
            cmd = f"tmux resize-window -t {session_id} -x {cols} -y {rows}"
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(
                    f"Failed to resize tmux session {session_id}: {stderr.decode()}"
                )
                return False

            logger.debug(f"Resized tmux session {session_id} to {cols}x{rows}")
            return True

        except Exception as e:
            logger.error(f"Error resizing tmux session {session_id}: {e}")
            return False

    async def capture_session_output(self, session_id: str) -> Optional[str]:
        """Capture current output from a tmux session"""
        try:
            if not await self._session_exists(session_id):
                return None

            cmd = f"tmux capture-pane -t {session_id} -p"
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(
                    f"Failed to capture tmux session {session_id}: {stderr.decode()}"
                )
                return None

            return stdout.decode()

        except Exception as e:
            logger.error(f"Error capturing tmux session {session_id}: {e}")
            return None

    async def list_sessions(
        self, user_id: Optional[str] = None, environment_id: Optional[str] = None
    ) -> List[str]:
        """List tmux sessions filtered by user or environment"""
        try:
            if user_id:
                return list(self.user_sessions.get(user_id, set()))
            elif environment_id:
                return list(self.environment_sessions.get(environment_id, set()))
            else:
                return list(self.sessions.keys())

        except Exception as e:
            logger.error(f"Error listing tmux sessions: {e}")
            return []

    async def kill_session(self, session_id: str) -> bool:
        """Kill a tmux session"""
        try:
            if await self._session_exists(session_id):
                cmd = f"tmux kill-session -t {session_id}"
                process = await asyncio.create_subprocess_shell(
                    cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                if process.returncode != 0:
                    logger.error(
                        f"Failed to kill tmux session {session_id}: {stderr.decode()}"
                    )

            # Clean up tracking
            await self._cleanup_session(session_id)
            logger.info(f"Killed tmux session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error killing tmux session {session_id}: {e}")
            return False

    async def kill_user_sessions(self, user_id: str) -> int:
        """Kill all tmux sessions for a user"""
        session_ids = list(self.user_sessions.get(user_id, set()))
        killed_count = 0

        for session_id in session_ids:
            if await self.kill_session(session_id):
                killed_count += 1

        logger.info(f"Killed {killed_count} tmux sessions for user {user_id}")
        return killed_count

    async def kill_environment_sessions(self, environment_id: str) -> int:
        """Kill all tmux sessions for an environment"""
        session_ids = list(self.environment_sessions.get(environment_id, set()))
        killed_count = 0

        for session_id in session_ids:
            if await self.kill_session(session_id):
                killed_count += 1

        logger.info(
            f"Killed {killed_count} tmux sessions for environment {environment_id}"
        )
        return killed_count

    async def cleanup_inactive_sessions(self, max_idle_seconds: int = 3600) -> int:
        """Clean up inactive tmux sessions"""
        current_time = asyncio.get_event_loop().time()
        inactive_sessions = []

        for session_id, session in self.sessions.items():
            if current_time - session.last_activity > max_idle_seconds:
                if not await self._session_exists(session_id):
                    inactive_sessions.append(session_id)

        cleaned_count = 0
        for session_id in inactive_sessions:
            await self._cleanup_session(session_id)
            cleaned_count += 1

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} inactive tmux sessions")

        return cleaned_count

    async def _session_exists(self, session_id: str) -> bool:
        """Check if a tmux session exists"""
        try:
            cmd = f"tmux has-session -t {session_id}"
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            await process.communicate()
            return process.returncode == 0

        except Exception as e:
            logger.error(f"Error checking tmux session {session_id}: {e}")
            return False

    async def _cleanup_session(self, session_id: str):
        """Clean up session tracking"""
        session = self.sessions.get(session_id)
        if session:
            # Remove from user sessions
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_id)
                if not self.user_sessions[session.user_id]:
                    del self.user_sessions[session.user_id]

            # Remove from environment sessions
            if session.environment_id in self.environment_sessions:
                self.environment_sessions[session.environment_id].discard(session_id)
                if not self.environment_sessions[session.environment_id]:
                    del self.environment_sessions[session.environment_id]

            # Remove session
            del self.sessions[session_id]


# Global tmux session manager instance
tmux_manager = TmuxSessionManager()
