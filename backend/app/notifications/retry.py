"""Bounded retry manager with exponential backoff and loop prevention (Task 34, Spec 57-59, 103)."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from app.notifications.models import NotificationDeliveryModel
from app.notifications.schemas import DeliveryStatus

logger = logging.getLogger("kairo.notifications.retry")


class DeliveryRetryManager:
    """
    Manages bounded retries for transient delivery failures.
    Invariant (Spec 57, 103): Never retries permanent auth/revocation failures.
    No Notification Loop: Delivery failures never emit failure notifications.
    """

    NON_RETRYABLE_KEYWORDS = (
        "unauthorized",
        "access denied",
        "revoked",
        "invalid destination",
        "forbidden",
        "not found",
    )

    def __init__(self, max_retries: int = 3, base_backoff_seconds: int = 2, max_backoff_seconds: int = 60) -> None:
        self.max_retries = max_retries
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds

    def is_retryable(self, error_message: str | None, attempts: int) -> bool:
        """Evaluate if delivery failure qualifies for another retry attempt."""
        if attempts >= self.max_retries:
            return False

        if not error_message:
            return True

        err_lower = error_message.lower()
        for kw in self.NON_RETRYABLE_KEYWORDS:
            if kw in err_lower:
                logger.info("Non-retryable delivery failure keyword detected: '%s'", kw)
                return False

        return True

    def calculate_backoff_seconds(self, attempts: int) -> int:
        """Bounded exponential backoff: min(base * 2^(attempts-1), max_backoff)."""
        backoff = self.base_backoff_seconds * (2 ** max(0, attempts - 1))
        return min(backoff, self.max_backoff_seconds)
