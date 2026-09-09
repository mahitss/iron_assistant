"""Scoped, versioned state caching layer with stampede protection (Task 39, Spec 50-57, 162)."""

import asyncio
import logging
import time
from typing import Any

logger = logging.getLogger("kairo.state.cache")


class CachedRecord:
    """In-memory or serialized cached state representation."""

    def __init__(
        self,
        key: str,
        value: Any,
        version: int,
        ttl_seconds: float = 300.0,
    ) -> None:
        self.key = key
        self.value = value
        self.version = version
        self.created_at = time.time()
        self.expires_at = self.created_at + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class ScopedStateCache:
    """Cache abstraction enforcing security scoping, version checking, and stampede prevention."""

    def __init__(self, default_ttl: float = 300.0) -> None:
        self.default_ttl = default_ttl
        self._entries: dict[str, CachedRecord] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    @classmethod
    def build_scoped_key(
        cls,
        domain: str,
        resource_id: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> str:
        """Constructs a security-scoped cache key.
        
        Invariant: Never allow the same key to expose different users' or projects' data.
        """
        u_part = f":u_{user_id}" if user_id else ""
        p_part = f":p_{project_id}" if project_id else ""
        return f"{domain}:{resource_id}{u_part}{p_part}"

    def get(
        self,
        key: str,
        min_required_version: int | None = None,
    ) -> Any | None:
        """Retrieves cached value if present, unexpired, and at least min_required_version."""
        entry = self._entries.get(key)
        if entry is None:
            return None

        # 1. Check TTL expiration
        if entry.is_expired:
            del self._entries[key]
            return None

        # 2. Check version freshness (Spec 54)
        if min_required_version is not None and entry.version < min_required_version:
            logger.debug(
                "Cached item '%s' v%d is older than required v%d; invalidating stale cache",
                key,
                entry.version,
                min_required_version,
            )
            del self._entries[key]
            return None

        return entry.value

    def put(
        self,
        key: str,
        value: Any,
        version: int,
        ttl_seconds: float | None = None,
    ) -> None:
        """Stores a scoped, versioned record in cache."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        self._entries[key] = CachedRecord(
            key=key,
            value=value,
            version=version,
            ttl_seconds=ttl,
        )

    def invalidate(self, key: str) -> None:
        """Removes a specific key from cache."""
        self._entries.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidates all keys matching a prefix (e.g. domain or resource)."""
        keys_to_del = [k for k in self._entries if k.startswith(prefix)]
        for k in keys_to_del:
            del self._entries[k]
        return len(keys_to_del)

    async def get_or_set_stampede_protected(
        self,
        key: str,
        fetcher: Any,
        version: int = 1,
        ttl_seconds: float | None = None,
    ) -> Any:
        """Fetches from cache or executes fetcher under a per-key lock to prevent stampedes (Spec 55)."""
        cached = self.get(key)
        if cached is not None:
            return cached

        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            # Double-check after acquiring lock
            cached = self.get(key)
            if cached is not None:
                return cached

            try:
                if asyncio.iscoroutinefunction(fetcher):
                    fresh_value = await fetcher()
                else:
                    fresh_value = fetcher()

                self.put(key, fresh_value, version=version, ttl_seconds=ttl_seconds)
                return fresh_value
            finally:
                self._locks.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()
        self._locks.clear()


# Global scoped cache
scoped_cache = ScopedStateCache()
