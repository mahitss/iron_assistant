"""Notification volume throttling, storm detection, and self-throttling defenses (Task 34, Spec 54-56, 104)."""

from collections import deque
from datetime import UTC, datetime, timedelta
import logging
from typing import Any

from app.notifications.schemas import NotificationPriority, NotificationType

logger = logging.getLogger("kairo.notifications.throttling")


class NotificationThrottler:
    """
    Guards against notification storms and enforces per-minute and per-hour volume limits.
    Storm Safety (Spec 56): Never suppresses URGENT security events, approvals, or critical task failures.
    Self-Throttling (Spec 104): Dampens non-critical volume when internal errors are elevated.
    """

    def __init__(
        self,
        rate_limit_per_minute: int = 30,
        rate_limit_per_hour: int = 200,
        storm_threshold: int = 20,
        storm_window_seconds: int = 10,
    ) -> None:
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_per_hour = rate_limit_per_hour
        self.storm_threshold = storm_threshold
        self.storm_window_seconds = storm_window_seconds

        # Sliding window timestamps: user_id -> deque of datetimes
        self._user_timestamps: dict[str, deque[datetime]] = {}
        # Storm window timestamps: user_id -> deque of datetimes
        self._storm_timestamps: dict[str, deque[datetime]] = {}
        # Active storm state: user_id -> storm_start_datetime
        self._active_storms: dict[str, datetime] = {}
        # Internal error tracking for self-throttling
        self._consecutive_delivery_failures: int = 0

    def record_delivery_outcome(self, success: bool) -> None:
        """Track delivery success/failure for self-throttling (Spec 104)."""
        if success:
            self._consecutive_delivery_failures = max(0, self._consecutive_delivery_failures - 1)
        else:
            self._consecutive_delivery_failures += 1
            if self._consecutive_delivery_failures >= 5:
                logger.warning(
                    "Self-throttling activated: %d consecutive delivery failures observed.",
                    self._consecutive_delivery_failures,
                )

    def is_storm_safe_priority(self, notification_type: NotificationType, priority: NotificationPriority) -> bool:
        """Urgent security, approval, and critical tasks MUST NOT be suppressed during a storm (Spec 56)."""
        if priority == NotificationPriority.URGENT:
            return True
        if notification_type in (NotificationType.APPROVAL, NotificationType.SECURITY):
            return True
        return False

    def check_throttle(
        self,
        user_id: str,
        notification_type: NotificationType,
        priority: NotificationPriority,
    ) -> tuple[bool, bool, str | None]:
        """
        Evaluate rate limit and storm condition.
        Returns:
            (allowed, is_storm, message)
        """
        # Always allow critical security & approvals through unconditionally
        if self.is_storm_safe_priority(notification_type, priority):
            return True, False, None

        now = datetime.now(UTC)

        # 1. Self-throttling check (Spec 104)
        if self._consecutive_delivery_failures >= 10 and priority == NotificationPriority.LOW:
            logger.info("Self-throttling suppressed LOW priority notification for user '%s'.", user_id)
            return False, False, "System self-throttling active"

        # 2. Storm detection window (e.g. >20 events in 10 seconds)
        if user_id not in self._storm_timestamps:
            self._storm_timestamps[user_id] = deque()
        storm_q = self._storm_timestamps[user_id]
        storm_cutoff = now - timedelta(seconds=self.storm_window_seconds)
        while storm_q and storm_q[0] < storm_cutoff:
            storm_q.popleft()
        storm_q.append(now)

        if len(storm_q) >= self.storm_threshold:
            # Active storm detected!
            self._active_storms[user_id] = now
            logger.critical("Notification storm detected for user '%s' (%d events in %ds).", user_id, len(storm_q), self.storm_window_seconds)
            return False, True, f"Notification storm in progress: {len(storm_q)} events detected in the last {self.storm_window_seconds}s."

        # Check if recovering from active storm within last 30s
        last_storm = self._active_storms.get(user_id)
        if last_storm and (now - last_storm).total_seconds() < 30:
            return False, True, "Recovering from notification storm; low priority events aggregated."

        # 3. Standard rate limiting (per minute and per hour)
        if user_id not in self._user_timestamps:
            self._user_timestamps[user_id] = deque()
        user_q = self._user_timestamps[user_id]

        hour_cutoff = now - timedelta(hours=1)
        minute_cutoff = now - timedelta(minutes=1)

        while user_q and user_q[0] < hour_cutoff:
            user_q.popleft()

        minute_count = sum(1 for t in user_q if t >= minute_cutoff)
        hour_count = len(user_q)

        if minute_count >= self.rate_limit_per_minute:
            logger.warning("Per-minute rate limit exceeded for user '%s' (%d/%d).", user_id, minute_count, self.rate_limit_per_minute)
            return False, False, f"Rate limit exceeded: {minute_count} notifications in the last minute."

        if hour_count >= self.rate_limit_per_hour:
            logger.warning("Per-hour rate limit exceeded for user '%s' (%d/%d).", user_id, hour_count, self.rate_limit_per_hour)
            return False, False, f"Rate limit exceeded: {hour_count} notifications in the last hour."

        user_q.append(now)
        return True, False, None
