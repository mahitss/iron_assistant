"""Explicit timeout management, nested deadline propagation, and budget enforcement."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, TypeVar

from app.resilience.schemas import utc_now

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DeadlineExceededError(Exception):
    """Raised when an operation or task exceeds its allocated deadline."""
    def __init__(self, operation: str, allocated_seconds: float):
        self.operation = operation
        self.allocated_seconds = allocated_seconds
        super().__init__(f"Operation '{operation}' exceeded allocated deadline of {allocated_seconds:.2f}s")


class DeadlineManager:
    """Manages hierarchical execution deadlines and remaining timeout budgets."""

    def __init__(self, deadline: datetime | None = None, timeout_seconds: float | None = None) -> None:
        now = utc_now()
        if deadline:
            self.deadline = deadline
        elif timeout_seconds:
            self.deadline = now + timedelta(seconds=timeout_seconds)
        else:
            # Default unbounded deadline (24 hours)
            self.deadline = now + timedelta(hours=24)

    def remaining_seconds(self) -> float:
        """Returns the remaining time budget in seconds (can be negative if expired)."""
        now = utc_now()
        return (self.deadline - now).total_seconds()

    def is_expired(self) -> bool:
        return self.remaining_seconds() <= 0.0

    def check_deadline(self, operation: str = "current_operation") -> None:
        """Throws DeadlineExceededError if the deadline has already passed."""
        rem = self.remaining_seconds()
        if rem <= 0.0:
            logger.warning("Resilience: Deadline exceeded before starting '%s' (remaining: %.2fs)", operation, rem)
            raise DeadlineExceededError(operation, 0.0)

    def derive_child_timeout(self, desired_timeout_seconds: float) -> float:
        """Returns a timeout that respects the parent deadline budget without exceeding it."""
        rem = self.remaining_seconds()
        if rem <= 0.0:
            return 0.001
        return min(desired_timeout_seconds, rem)

    async def execute_with_deadline(
        self,
        func: Callable[[], Awaitable[T]],
        operation: str,
        desired_timeout_seconds: float | None = None,
    ) -> T:
        """Executes an async function bounded by the minimum of desired timeout and remaining deadline."""
        self.check_deadline(operation)
        rem = self.remaining_seconds()
        effective_timeout = min(desired_timeout_seconds or rem, rem)

        try:
            return await asyncio.wait_for(func(), timeout=effective_timeout)
        except asyncio.TimeoutError as exc:
            logger.warning(
                "Resilience: Operation '%s' timed out after %.2f seconds (parent budget: %.2fs)",
                operation, effective_timeout, rem
            )
            raise DeadlineExceededError(operation, effective_timeout) from exc
