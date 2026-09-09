"""Deadline Tracking, Time Propagation, and Safe Timeout Handling (Task 45)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("kairo.autonomy.deadlines")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeadlineExhaustedError(Exception):
    """Raised when an autonomous run exceeds its global SLA deadline."""


class DeadlineTracker:
    """Tracks autonomous run deadlines and propagates remaining SLA time to sub-components (Spec 51-53)."""

    def __init__(self, deadline: Optional[datetime] = None) -> None:
        self.deadline = deadline

    @property
    def is_expired(self) -> bool:
        if not self.deadline:
            return False
        return utc_now() >= self.deadline

    @property
    def remaining_seconds(self) -> Optional[float]:
        if not self.deadline:
            return None
        diff = (self.deadline - utc_now()).total_seconds()
        return max(0.0, diff)

    def validate_deadline(self) -> None:
        """Verify that run has not exceeded its deadline (Spec 53)."""
        if self.is_expired:
            logger.warning("Autonomous run deadline expired at %s", self.deadline.isoformat() if self.deadline else "None")
            raise DeadlineExhaustedError(f"EXPIRED: Run deadline exceeded at {self.deadline}")

    def propagate_step_timeout(self, max_step_timeout: float = 60.0) -> float:
        """Calculate safe bounded timeout for sub-tasks or tool calls (Spec 52)."""
        rem = self.remaining_seconds
        if rem is None:
            return max_step_timeout
        # Allocate at most 80% of remaining time or step max
        return max(1.0, min(max_step_timeout, rem * 0.8))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "is_expired": self.is_expired,
            "remaining_seconds": round(self.remaining_seconds, 1) if self.remaining_seconds is not None else None,
        }
