"""File-backed session persistence for Consilium.

Stores session state as JSON on disk with in-memory caching.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import aiofiles
import aiofiles.os

from backend.config import Settings, get_settings
from backend.lib.exceptions import (
    SessionExpiredError,
    SessionNotFoundError,
    SessionPersistenceError,
)
from backend.lib.models import SessionState

logger = logging.getLogger(__name__)


class CacheEntry:
    """An entry in the session cache."""

    def __init__(self, session: SessionState, ttl_hours: int = 1):
        self.session = session
        self.expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
        self.last_accessed = datetime.utcnow()

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        self.last_accessed = datetime.utcnow()


class SessionStore:
    """
    File-backed session storage with in-memory caching.

    Features:
    - Async save/load of session state as JSON
    - In-memory cache with configurable TTL
    - Auto-flush on major state transitions
    - Session recovery for SSE reconnects
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._cache: dict[UUID, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self._cache_ttl_hours = 1
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the session store."""
        if self._initialized:
            return

        # Ensure session directory exists
        self.settings.ensure_session_dir()
        self._initialized = True
        logger.info(f"Session store initialized at {self.settings.session_dir}")

    async def shutdown(self) -> None:
        """Shutdown and flush all cached sessions."""
        async with self._lock:
            for session_id, entry in self._cache.items():
                try:
                    await self._write_to_disk(entry.session)
                except Exception as e:
                    logger.error(f"Failed to flush session {session_id}: {e}")
            self._cache.clear()
        logger.info("Session store shut down")

    def _get_path(self, session_id: UUID) -> Path:
        """Get file path for a session."""
        return self.settings.session_dir / f"{session_id}.json"

    async def _read_from_disk(self, session_id: UUID) -> SessionState | None:
        """Read session from disk."""
        path = self._get_path(session_id)
        if not path.exists():
            return None

        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
            return SessionState.model_validate_json(content)
        except Exception as e:
            logger.error(f"Failed to read session {session_id} from disk: {e}")
            return None

    async def _write_to_disk(self, session: SessionState) -> None:
        """Write session to disk."""
        path = self._get_path(session.session_id)
        try:
            content = session.model_dump_json(indent=2)
            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                await f.write(content)
            logger.debug(f"Session {session.session_id} written to disk")
        except Exception as e:
            logger.error(f"Failed to write session {session.session_id} to disk: {e}")
            raise SessionPersistenceError(f"Failed to persist session: {e}")

    async def _delete_from_disk(self, session_id: UUID) -> None:
        """Delete session from disk."""
        path = self._get_path(session_id)
        if path.exists():
            try:
                await aiofiles.os.remove(path)
                logger.debug(f"Session {session_id} deleted from disk")
            except Exception as e:
                logger.error(f"Failed to delete session {session_id}: {e}")

    def _is_session_expired(self, session: SessionState) -> bool:
        """Check if session has expired based on TTL."""
        age = datetime.utcnow() - session.created_at
        return age > timedelta(hours=self.settings.session_ttl_hours)

    async def create(self, session: SessionState | None = None) -> SessionState:
        """
        Create a new session.

        Args:
            session: Optional pre-configured session. Creates new if not provided.

        Returns:
            The created session
        """
        await self.initialize()

        if session is None:
            session = SessionState()

        async with self._lock:
            # Add to cache
            self._cache[session.session_id] = CacheEntry(
                session, self._cache_ttl_hours
            )

        # Persist to disk
        await self._write_to_disk(session)

        logger.info(f"Created session {session.session_id}")
        return session

    async def get(self, session_id: UUID) -> SessionState:
        """
        Get a session by ID.

        Args:
            session_id: Session UUID

        Returns:
            SessionState

        Raises:
            SessionNotFoundError: If session doesn't exist
            SessionExpiredError: If session has expired
        """
        await self.initialize()

        async with self._lock:
            # Check cache first
            if session_id in self._cache:
                entry = self._cache[session_id]
                if not entry.is_expired():
                    entry.touch()
                    if self._is_session_expired(entry.session):
                        raise SessionExpiredError(str(session_id))
                    return entry.session
                else:
                    # Cache entry expired, remove it
                    del self._cache[session_id]

        # Not in cache, try disk
        session = await self._read_from_disk(session_id)
        if session is None:
            raise SessionNotFoundError(str(session_id))

        if self._is_session_expired(session):
            raise SessionExpiredError(str(session_id))

        # Add to cache
        async with self._lock:
            self._cache[session_id] = CacheEntry(session, self._cache_ttl_hours)

        return session

    async def save(self, session: SessionState) -> None:
        """
        Save a session (update cache and persist to disk).

        Args:
            session: Session to save
        """
        await self.initialize()

        session.touch()

        async with self._lock:
            self._cache[session.session_id] = CacheEntry(
                session, self._cache_ttl_hours
            )

        await self._write_to_disk(session)

    async def delete(self, session_id: UUID) -> None:
        """
        Delete a session.

        Args:
            session_id: Session to delete
        """
        async with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]

        await self._delete_from_disk(session_id)
        logger.info(f"Deleted session {session_id}")

    async def exists(self, session_id: UUID) -> bool:
        """Check if a session exists."""
        async with self._lock:
            if session_id in self._cache:
                return True

        path = self._get_path(session_id)
        return path.exists()

    async def cleanup_expired(self) -> int:
        """
        Clean up expired sessions.

        Returns:
            Number of sessions cleaned up
        """
        await self.initialize()
        cleaned = 0

        # Clean cache
        async with self._lock:
            expired_cache = [
                sid for sid, entry in self._cache.items() if entry.is_expired()
            ]
            for sid in expired_cache:
                del self._cache[sid]
                cleaned += 1

        # Clean disk
        try:
            for path in self.settings.session_dir.glob("*.json"):
                try:
                    async with aiofiles.open(path, "r", encoding="utf-8") as f:
                        content = await f.read()
                    session = SessionState.model_validate_json(content)
                    if self._is_session_expired(session):
                        await aiofiles.os.remove(path)
                        cleaned += 1
                        logger.debug(f"Cleaned up expired session {path.stem}")
                except Exception as e:
                    logger.warning(f"Error checking session {path}: {e}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired sessions")

        return cleaned

    async def list_sessions(self) -> list[UUID]:
        """List all session IDs."""
        await self.initialize()

        session_ids = set()

        # From cache
        async with self._lock:
            session_ids.update(self._cache.keys())

        # From disk
        for path in self.settings.session_dir.glob("*.json"):
            try:
                session_ids.add(UUID(path.stem))
            except ValueError:
                pass

        return list(session_ids)

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_sessions": len(self._cache),
            "cache_ttl_hours": self._cache_ttl_hours,
            "session_dir": str(self.settings.session_dir),
            "session_ttl_hours": self.settings.session_ttl_hours,
        }


# =============================================================================
# Module-level store instance
# =============================================================================


_default_store: SessionStore | None = None


async def get_session_store() -> SessionStore:
    """Get the default session store instance."""
    global _default_store
    if _default_store is None:
        _default_store = SessionStore()
        await _default_store.initialize()
    return _default_store


async def close_session_store() -> None:
    """Close the default session store."""
    global _default_store
    if _default_store:
        await _default_store.shutdown()
        _default_store = None
