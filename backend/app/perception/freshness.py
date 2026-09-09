"""Freshness Tracking, Clock Skew Compensation, and Stale Overwrite Protection (Task 46)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Dict, Optional

logger = logging.getLogger("kairo.perception.freshness")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FreshnessTracker:
    """Manages clock skew calculations, observation freshness, and prevents stale state overwrites (Spec 20-23, 61)."""

    def __init__(self, default_ttl_seconds: float = 60.0) -> None:
        self.default_ttl = default_ttl_seconds
        # subject -> latest_observed_timestamp
        self._latest_observed: Dict[str, datetime] = {}
        # source_id -> measured clock skew (in seconds)
        self._clock_skews: Dict[str, float] = {}

    def calculate_clock_skew(self, source_id: str, source_timestamp: datetime, received_timestamp: datetime) -> float:
        """Measure source clock skew relative to receiver system clock (Spec 21)."""
        skew_seconds = (source_timestamp - received_timestamp).total_seconds()
        self._clock_skews[source_id] = skew_seconds
        if abs(skew_seconds) > 5.0:
            logger.warning("Clock skew detected for source %s: %.2fs", source_id, skew_seconds)
        return skew_seconds

    def is_stale_update(self, subject: str, candidate_timestamp: datetime) -> bool:
        """Enforce Spec 20: Prevent delayed or old events from overwriting newer verified state."""
        last = self._latest_observed.get(subject)
        if not last:
            self._latest_observed[subject] = candidate_timestamp
            return False

        if candidate_timestamp < last:
            logger.info("Stale update rejected for subject '%s': candidate (%s) < latest (%s)", subject, candidate_timestamp.isoformat(), last.isoformat())
            return True

        self._latest_observed[subject] = candidate_timestamp
        return False

    def is_observation_fresh(self, observed_at: datetime, ttl_seconds: Optional[float] = None) -> bool:
        """Check if an observation is still valid or has expired (Spec 61)."""
        ttl = ttl_seconds or self.default_ttl
        age = (utc_now() - observed_at).total_seconds()
        return age <= ttl

    def get_latest_observed_time(self, subject: str) -> Optional[datetime]:
        return self._latest_observed.get(subject)

    def record_observation_timestamp(self, subject: str, timestamp: datetime) -> None:
        self._latest_observed[subject] = timestamp

