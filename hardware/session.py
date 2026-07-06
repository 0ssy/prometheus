from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DeviceSession:
    """Represents an active hardware device session."""

    session_id: str
    device_id: str
    driver_name: str
    transport: str
    connected_at: datetime = field(default_factory=utc_now)
    last_activity: datetime = field(default_factory=utc_now)
    retries: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300


class DeviceSessionManager:
    """Manages active device sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, DeviceSession] = {}
        self._lock = threading.Lock()

    def create_session(self, device_id: str, driver_name: str, **kwargs: Any) -> DeviceSession:
        """Create a new device session."""
        with self._lock:
            session_id = f"{driver_name}:{device_id}"
            session = DeviceSession(
                session_id=session_id,
                device_id=device_id,
                driver_name=driver_name,
                transport=kwargs.get("transport", "unknown"),
                connected_at=utc_now(),
                last_activity=utc_now(),
                retries=kwargs.get("retries", 0),
                max_retries=kwargs.get("max_retries", 3),
                timeout_seconds=kwargs.get("timeout_seconds", 300),
            )
            self._sessions[session_id] = session
            logger.info(f"Created session: {session_id}")
            return session

    def get_session(self, session_id: str) -> DeviceSession | None:
        """Retrieve a session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> None:
        """Close and remove a session by ID."""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Closed session: {session_id}")

    def list_sessions(self) -> list[DeviceSession]:
        """Return all active sessions."""
        with self._lock:
            return list(self._sessions.values())

    def refresh_session(self, session_id: str) -> DeviceSession | None:
        """Refresh the last activity timestamp of a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.last_activity = utc_now()
            return session

    def cleanup_expired(self) -> list[str]:
        """Remove expired sessions and return their IDs."""
        expired: list[str] = []
        now = utc_now()
        with self._lock:
            for session_id, session in list(self._sessions.items()):
                elapsed = (now - session.last_activity).total_seconds()
                if elapsed > session.timeout_seconds:
                    expired.append(session_id)
                    del self._sessions[session_id]
                    logger.info(f"Expired session: {session_id}")
        return expired
