"""Ephemeral conversation and session state management with Redis and in-memory fallback."""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger("kairo.memory.session")


class SessionManager:
    """Manages short-lived conversation session cache with graceful fallback if Redis is down."""

    def __init__(self, redis_url: str | None = None, default_ttl: int = 3600):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._redis: aioredis.Redis | None = None
        self._in_memory_cache: dict[str, dict[str, Any]] = {}
        self._redis_available: bool = True

    async def _get_client(self) -> aioredis.Redis | None:
        """Lazy-initialize and return active Redis connection."""
        if not self.redis_url:
            return None

        if self._redis is None and self._redis_available:
            try:
                self._redis = aioredis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2.0,
                    socket_timeout=2.0,
                )
                # Test connectivity
                await self._redis.ping()
            except Exception as exc:
                logger.warning("Redis is unavailable (%s). Falling back to in-memory session cache.", exc)
                self._redis_available = False
                self._redis = None

        return self._redis

    async def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve cached ephemeral session metadata."""
        key = f"kairo:session:{session_id}"
        client = await self._get_client()

        if client is not None:
            try:
                data = await client.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception as exc:
                logger.warning("Error reading session from Redis: %s", exc)

        return self._in_memory_cache.get(session_id)

    async def set_session_state(
        self,
        session_id: str,
        state: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Store ephemeral session metadata with TTL."""
        key = f"kairo:session:{session_id}"
        expiry = ttl or self.default_ttl
        serialized = json.dumps(state)
        client = await self._get_client()

        if client is not None:
            try:
                await client.setex(key, expiry, serialized)
                return
            except Exception as exc:
                logger.warning("Error writing session to Redis: %s", exc)

        self._in_memory_cache[session_id] = state

    async def clear_session_state(self, session_id: str) -> None:
        """Clear ephemeral session state."""
        key = f"kairo:session:{session_id}"
        client = await self._get_client()

        if client is not None:
            try:
                await client.delete(key)
            except Exception as exc:
                logger.warning("Error deleting session from Redis: %s", exc)

        self._in_memory_cache.pop(session_id, None)

    async def close(self) -> None:
        """Close Redis connection pool cleanly."""
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None


def get_default_session_manager() -> SessionManager:
    """Instantiate standard session manager with configured Redis settings."""
    settings = get_settings()
    return SessionManager(
        redis_url=settings.REDIS_URL,
        default_ttl=settings.KAIRO_REDIS_TTL_SECONDS,
    )
