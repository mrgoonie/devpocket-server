import asyncio
import os
import select
import signal
import threading
from typing import Callable, Dict, Optional

import structlog
from ptyprocess import PtyProcess

logger = structlog.get_logger(__name__)


class PTYSession:
    """Manages a PTY session for terminal interaction"""

    def __init__(
        self,
        session_id: str,
        environment_id: str,
        user_id: str,
        output_callback: Callable[[str], None],
    ):
        self.session_id = session_id
        self.environment_id = environment_id
        self.user_id = user_id
        self.output_callback = output_callback

        self.pty_process: Optional[PtyProcess] = None
        self.read_thread: Optional[threading.Thread] = None
        self.is_running = False

        # Terminal settings
        self.cols = 80
        self.rows = 24

    async def start(self, shell_command: str = "/bin/bash"):
        """Start PTY session"""
        try:
            logger.info(f"Starting PTY session {self.session_id}")

            # Start PTY process
            self.pty_process = PtyProcess.spawn(
                [shell_command, "-l"],  # Login shell
                dimensions=(self.rows, self.cols),
                env=self._get_environment_variables(),
            )

            self.is_running = True

            # Start reading output in background thread
            self.read_thread = threading.Thread(
                target=self._read_output_loop, daemon=True
            )
            self.read_thread.start()

            logger.info(f"PTY session {self.session_id} started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start PTY session {self.session_id}: {e}")
            return False

    def _get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for PTY process"""
        env = os.environ.copy()
        env.update(
            {
                "TERM": "xterm-256color",
                "PS1": r"\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ ",
                "SHELL": "/bin/bash",
                "HOME": "/home/devuser",
                "USER": "devuser",
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            }
        )
        return env

    def _read_output_loop(self):
        """Read output from PTY in background thread"""
        try:
            while self.is_running and self.pty_process and self.pty_process.isalive():
                try:
                    # Use select to check for available data
                    ready, _, _ = select.select([self.pty_process.fd], [], [], 0.1)

                    if ready:
                        # Read available data
                        data = self.pty_process.read(1024)
                        if data:
                            # Send to output callback
                            self.output_callback(data.decode("utf-8", errors="replace"))

                except (OSError, EOFError) as e:
                    logger.debug(f"PTY read error (process may have ended): {e}")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error reading PTY output: {e}")
                    break

        except Exception as e:
            logger.error(f"PTY read loop error: {e}")
        finally:
            logger.info(f"PTY read loop ended for session {self.session_id}")

    async def write_input(self, data: str):
        """Write input to PTY"""
        try:
            if self.pty_process and self.pty_process.isalive():
                self.pty_process.write(data.encode("utf-8"))
                return True
            else:
                logger.warning(f"PTY process not alive for session {self.session_id}")
                return False
        except Exception as e:
            logger.error(f"Error writing to PTY session {self.session_id}: {e}")
            return False

    async def resize(self, cols: int, rows: int):
        """Resize PTY terminal"""
        try:
            self.cols = cols
            self.rows = rows

            if self.pty_process and self.pty_process.isalive():
                self.pty_process.setwinsize(rows, cols)
                logger.debug(f"PTY session {self.session_id} resized to {cols}x{rows}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error resizing PTY session {self.session_id}: {e}")
            return False

    async def stop(self):
        """Stop PTY session"""
        try:
            self.is_running = False

            if self.pty_process and self.pty_process.isalive():
                # Send SIGTERM first
                self.pty_process.kill(signal.SIGTERM)

                # Wait a bit for graceful shutdown
                for _ in range(10):  # Wait up to 1 second
                    if not self.pty_process.isalive():
                        break
                    await asyncio.sleep(0.1)

                # Force kill if still alive
                if self.pty_process.isalive():
                    self.pty_process.kill(signal.SIGKILL)

            # Wait for read thread to finish
            if self.read_thread and self.read_thread.is_alive():
                self.read_thread.join(timeout=2.0)

            logger.info(f"PTY session {self.session_id} stopped")

        except Exception as e:
            logger.error(f"Error stopping PTY session {self.session_id}: {e}")


class PTYManager:
    """Manages multiple PTY sessions"""

    def __init__(self):
        self.sessions: Dict[str, PTYSession] = {}
        self.user_sessions: Dict[str, set] = {}  # user_id -> set of session_ids

    async def create_session(
        self,
        session_id: str,
        environment_id: str,
        user_id: str,
        output_callback: Callable[[str], None],
        shell_command: str = "/bin/bash",
    ) -> bool:
        """Create new PTY session"""
        try:
            if session_id in self.sessions:
                logger.warning(f"PTY session {session_id} already exists")
                return False

            session = PTYSession(session_id, environment_id, user_id, output_callback)
            success = await session.start(shell_command)

            if success:
                self.sessions[session_id] = session

                # Track user sessions
                if user_id not in self.user_sessions:
                    self.user_sessions[user_id] = set()
                self.user_sessions[user_id].add(session_id)

                logger.info(f"Created PTY session {session_id} for user {user_id}")
                return True
            else:
                logger.error(f"Failed to create PTY session {session_id}")
                return False

        except Exception as e:
            logger.error(f"Error creating PTY session {session_id}: {e}")
            return False

    async def write_to_session(self, session_id: str, data: str) -> bool:
        """Write data to PTY session"""
        session = self.sessions.get(session_id)
        if session:
            return await session.write_input(data)
        else:
            logger.warning(f"PTY session {session_id} not found")
            return False

    async def resize_session(self, session_id: str, cols: int, rows: int) -> bool:
        """Resize PTY session"""
        session = self.sessions.get(session_id)
        if session:
            return await session.resize(cols, rows)
        else:
            logger.warning(f"PTY session {session_id} not found")
            return False

    async def close_session(self, session_id: str):
        """Close PTY session"""
        session = self.sessions.get(session_id)
        if session:
            await session.stop()

            # Remove from tracking
            del self.sessions[session_id]

            # Remove from user sessions
            if session.user_id in self.user_sessions:
                self.user_sessions[session.user_id].discard(session_id)
                if not self.user_sessions[session.user_id]:
                    del self.user_sessions[session.user_id]

            logger.info(f"Closed PTY session {session_id}")
        else:
            logger.warning(f"PTY session {session_id} not found for closing")

    async def close_user_sessions(self, user_id: str):
        """Close all PTY sessions for a user"""
        if user_id in self.user_sessions:
            session_ids = list(self.user_sessions[user_id])
            for session_id in session_ids:
                await self.close_session(session_id)
            logger.info(f"Closed {len(session_ids)} PTY sessions for user {user_id}")

    def get_session_count(self, user_id: str) -> int:
        """Get number of active sessions for user"""
        return len(self.user_sessions.get(user_id, set()))

    async def cleanup_inactive_sessions(self):
        """Clean up inactive PTY sessions"""
        inactive_sessions = []

        for session_id, session in self.sessions.items():
            if not session.pty_process or not session.pty_process.isalive():
                inactive_sessions.append(session_id)

        for session_id in inactive_sessions:
            logger.info(f"Cleaning up inactive PTY session {session_id}")
            await self.close_session(session_id)

        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive PTY sessions")


# Global PTY manager instance
pty_manager = PTYManager()
