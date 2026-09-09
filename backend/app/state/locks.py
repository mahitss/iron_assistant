"""Distributed lock manager with mandatory TTL expiration and fencing tokens (Task 39, Spec 58-60)."""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger("kairo.state.locks")


class LockAcquisitionError(Exception):
    """Raised when failing to acquire a state lock."""


class StaleFencingTokenError(Exception):
    """Raised when a worker attempts an operation with an outdated fencing token."""


class LockRecord:
    def __init__(self, key: str, owner: str, fencing_token: int, ttl_seconds: float) -> None:
        self.key = key
        self.owner = owner
        self.fencing_token = fencing_token
        self.expires_at = time.time() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class StateLockManager:
    """Manages distributed locks with mandatory expiration and monotonic fencing tokens."""

    def __init__(self) -> None:
        self._locks: dict[str, LockRecord] = {}
        self._fencing_counters: dict[str, int] = {}
        self._async_lock = asyncio.Lock()

    async def acquire_lock(
        self,
        key: str,
        owner: str,
        ttl_seconds: float = 30.0,
    ) -> int:
        """Acquires a lock for a key with mandatory expiration.
        
        Returns the monotonic fencing token.
        Never permits infinite locks.
        """
        async with self._async_lock:
            existing = self._locks.get(key)
            if existing is not None and not existing.is_expired:
                if existing.owner != owner:
                    raise LockAcquisitionError(
                        f"Lock on '{key}' already held by worker '{existing.owner}' until {existing.expires_at}"
                    )

            # Increment fencing token
            token = self._fencing_counters.get(key, 0) + 1
            self._fencing_counters[key] = token

            # Create new lock lease
            self._locks[key] = LockRecord(
                key=key,
                owner=owner,
                fencing_token=token,
                ttl_seconds=max(ttl_seconds, 1.0),  # Minimum 1 second, never infinite
            )
            logger.debug("Acquired lock on '%s' for owner '%s' (token=%d)", key, owner, token)
            return token

    async def release_lock(self, key: str, owner: str) -> bool:
        """Releases the lock if held by the owner."""
        async with self._async_lock:
            existing = self._locks.get(key)
            if existing is not None and existing.owner == owner:
                del self._locks[key]
                logger.debug("Released lock on '%s' by owner '%s'", key, owner)
                return True
            return False

    async def verify_fencing_token(self, key: str, token: int) -> None:
        """Validates that worker's fencing token is current and not superseded."""
        async with self._async_lock:
            current_token = self._fencing_counters.get(key, 0)
            if token < current_token:
                raise StaleFencingTokenError(
                    f"Fencing token {token} on key '{key}' is stale! Current token is {current_token}. Mutation rejected."
                )

    @asynccontextmanager
    async def lock(
        self,
        key: str,
        owner: str,
        ttl_seconds: float = 30.0,
    ):
        """Context manager for acquiring and safely releasing a lock."""
        token = await self.acquire_lock(key, owner, ttl_seconds=ttl_seconds)
        try:
            yield token
        finally:
            await self.release_lock(key, owner)

    def clear(self) -> None:
        self._locks.clear()
        self._fencing_counters.clear()


# Global lock manager
state_lock_manager = StateLockManager()
