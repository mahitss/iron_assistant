"""Predictive Monitoring, Budgeting, Resource Bounds, and Monitor Cleanup (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.monitors")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MonitorLifecycleState(str, Enum):
    """5 monitor lifecycle states (Spec 58)."""

    START = "START"
    WATCH = "WATCH"
    UPDATE = "UPDATE"
    CONFIRM = "CONFIRM"
    CLOSE = "CLOSE"


class MonitorBudgetExceededError(Exception):
    """Raised when active monitor count exceeds allowed operational budget (Spec 59)."""


@dataclass
class PredictionMonitor:
    """Active probe watching environmental telemetry to verify or expire a forecast (Spec 57-61, 157-159)."""

    monitor_id: str
    prediction_id: str
    subject: str
    poll_frequency_seconds: float = 30.0  # Bounded frequency (Spec 59)
    state: MonitorLifecycleState = MonitorLifecycleState.START
    max_checks: int = 100
    checks_performed: int = 0
    poll_count: int = 0
    created_at: datetime = field(default_factory=utc_now)
    last_checked_at: Optional[datetime] = None

    def tick(self) -> MonitorLifecycleState:
        """Advance monitor check with bounded budget."""
        self.checks_performed += 1
        self.poll_count += 1
        self.last_checked_at = utc_now()
        if self.checks_performed >= self.max_checks:
            self.state = MonitorLifecycleState.CLOSE
            logger.info("Monitor %s closed due to budget exhaustion (max checks=%d)", self.monitor_id, self.max_checks)
        else:
            self.state = MonitorLifecycleState.WATCH
        return self.state

    def record_poll(self, observed_evidence: Any = None) -> None:
        self.tick()

    def close(self) -> None:
        self.state = MonitorLifecycleState.CLOSE


class MonitorRegistry:
    """Manages active prediction monitors and cleans up orphaned monitors (Spec 158, 159)."""

    def __init__(self, max_active_monitors: int = 100) -> None:
        self.max_active_monitors = max_active_monitors
        # monitor_id -> PredictionMonitor
        self._monitors: Dict[str, PredictionMonitor] = {}

    def register_monitor(
        self,
        prediction_id: str,
        subject: str,
        poll_freq: float = 30.0,
        max_polls: int = 100,
    ) -> PredictionMonitor:
        active = self.get_active_monitors()
        if len(active) >= self.max_active_monitors:
            raise MonitorBudgetExceededError(
                f"Monitor budget exceeded: maximum {self.max_active_monitors} active monitors allowed (Spec 59)."
            )

        mid = f"mon_{uuid.uuid4().hex[:8]}"
        mon = PredictionMonitor(
            monitor_id=mid,
            prediction_id=prediction_id,
            subject=subject,
            poll_frequency_seconds=poll_freq,
            max_checks=max_polls,
        )
        self._monitors[mid] = mon
        logger.info("Registered prediction monitor %s on '%s'", mid, subject)
        return mon

    def cleanup_expired_monitors(self, active_prediction_ids: set[str]) -> int:
        """Enforce Spec 158, 159: Expired predictions remove associated monitors to prevent orphaned monitors."""
        to_remove = []
        for mid, mon in self._monitors.items():
            if mon.prediction_id not in active_prediction_ids or mon.state == MonitorLifecycleState.CLOSE:
                to_remove.append(mid)

        for mid in to_remove:
            del self._monitors[mid]

        if to_remove:
            logger.info("Cleaned up %d orphaned/closed prediction monitors", len(to_remove))
        return len(to_remove)

    def cleanup_expired(self, expired_ids: List[str]) -> int:
        to_remove = []
        for mid, mon in self._monitors.items():
            if mon.prediction_id in expired_ids:
                to_remove.append(mid)
        for mid in to_remove:
            del self._monitors[mid]
        return len(to_remove)

    def get_active_monitors(self) -> List[PredictionMonitor]:
        return [m for m in self._monitors.values() if m.state != MonitorLifecycleState.CLOSE]

    def list_active_monitors(self) -> List[PredictionMonitor]:
        return self.get_active_monitors()
