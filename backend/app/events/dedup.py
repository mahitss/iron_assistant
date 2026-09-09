"""Event Deduplicator for Kairo Unified Event Bus.

Tracks processed event IDs and domain idempotency keys across a sliding time window
to prevent duplicate delivery and replay side effects.
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, Optional

from app.config.settings import settings


class EventDeduplicator:
    """Sliding-window deduplication store for event delivery and processing."""

    def __init__(self, window_seconds: Optional[int] = None) -> None:
        self.window_seconds = (
            window_seconds
            if window_seconds is not None
            else getattr(settings, "KAIRO_EVENTS_DEDUP_WINDOW_SECONDS", 3600)
        )
        self._seen_keys: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def is_duplicate(self, key: str) -> bool:
        """Check whether key was already seen within the deduplication window."""
        if not key:
            return False
        now = time.time()
        async with self._lock:
            if key in self._seen_keys:
                timestamp = self._seen_keys[key]
                if now - timestamp <= self.window_seconds:
                    return True
                # Expired key
                del self._seen_keys[key]
            return False

    async def mark_seen(self, key: str) -> None:
        """Record key as seen at current timestamp."""
        if not key:
            return
        now = time.time()
        async with self._lock:
            self._seen_keys[key] = now
            if len(self._seen_keys) > 20000:
                self._prune_internal(now)

    async def check_and_mark(self, key: str) -> bool:
        """Atomically check if key is duplicate; if not duplicate, mark it seen.

        Returns True if duplicate (already seen), False if newly seen.
        """
        if not key:
            return False
        now = time.time()
        async with self._lock:
            if key in self._seen_keys:
                timestamp = self._seen_keys[key]
                if now - timestamp <= self.window_seconds:
                    return True
            self._seen_keys[key] = now
            if len(self._seen_keys) > 20000:
                self._prune_internal(now)
            return False

    def _prune_internal(self, now: float) -> int:
        expired = [k for k, ts in self._seen_keys.items() if now - ts > self.window_seconds]
        for k in expired:
            del self._seen_keys[k]
        return len(expired)

    async def prune(self) -> int:
        """Remove expired keys older than the sliding window."""
        now = time.time()
        async with self._lock:
            return self._prune_internal(now)

    async def clear(self) -> None:
        """Reset deduplication state."""
        async with self._lock:
            self._seen_keys.clear()

    async def size(self) -> int:
        """Get number of actively tracked keys."""
        async with self._lock:
            return len(self._seen_keys)
