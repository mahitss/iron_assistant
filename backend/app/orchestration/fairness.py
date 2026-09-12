"""Fairness and Anti-Starvation Engine: dynamic aging boost and multi-tenant fair-share metrics (Task 77)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.orchestration.economy_schemas import FairnessMetrics

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class FairnessEngine:
    """Computes dynamic anti-starvation priority aging and evaluates multi-tenant fair share."""

    def __init__(
        self,
        aging_factor_alpha: float = 0.5,
        max_priority_boost: float = 10.0,
        starvation_threshold_s: float = 60.0,
    ) -> None:
        self.aging_factor_alpha = aging_factor_alpha
        self.max_priority_boost = max_priority_boost
        self.starvation_threshold_s = starvation_threshold_s
        self._task_arrival_times: dict[str, datetime] = {}

    def record_task_arrival(self, task_id: str, arrival_time: datetime | None = None) -> None:
        """Record task arrival timestamp for wait tracking."""
        self._task_arrival_times[task_id] = arrival_time or _now_utc()

    def record_task_completion(self, task_id: str) -> None:
        """Remove task on completion or cancellation."""
        self._task_arrival_times.pop(task_id, None)

    def get_task_wait_time_s(self, task_id: str) -> float:
        """Get total waiting duration for a task in seconds."""
        arrival = self._task_arrival_times.get(task_id)
        if arrival is None:
            return 0.0
        return max(0.0, (_now_utc() - arrival).total_seconds())

    def calculate_effective_priority(
        self,
        task_id: str,
        base_priority: int,
        wait_time_s: float | None = None,
    ) -> float:
        """Compute effective priority with dynamic anti-starvation aging boost.

        Formula: P_eff = P_base + min(alpha * wait_time_s, max_boost)
        """
        if wait_time_s is None:
            wait_time_s = self.get_task_wait_time_s(task_id)

        boost = min(self.max_priority_boost, self.aging_factor_alpha * wait_time_s)
        return float(base_priority) + boost

    def is_starving(self, task_id: str, wait_time_s: float | None = None) -> bool:
        """Determine if a task has exceeded the starvation wait threshold."""
        if wait_time_s is None:
            wait_time_s = self.get_task_wait_time_s(task_id)
        return wait_time_s >= self.starvation_threshold_s

    def compute_fairness_metrics(
        self,
        tenant_shares: dict[str, float],
        task_wait_times: dict[str, float] | None = None,
    ) -> FairnessMetrics:
        """Compute Gini coefficient and Max-Min fairness across tenant resource shares."""
        values = list(tenant_shares.values())
        if not values or all(v == 0.0 for v in values):
            return FairnessMetrics(
                gini_coefficient=0.0,
                max_min_ratio=1.0,
                starvation_count=0,
                average_wait_time_s=0.0,
                calculated_at=_now_utc(),
            )

        n = len(values)
        total = sum(values)

        # Gini Coefficient Calculation
        # G = sum_i sum_j |x_i - x_j| / (2 * n * sum(x))
        if total > 0 and n > 1:
            diff_sum = sum(abs(xi - xj) for xi in values for xj in values)
            gini = diff_sum / (2.0 * n * total)
        else:
            gini = 0.0

        min_val = min(values)
        max_val = max(values)
        max_min_ratio = (max_val / min_val) if min_val > 0 else (max_val if max_val > 0 else 1.0)

        # Wait times & starvation stats
        waits = task_wait_times or {
            tid: self.get_task_wait_time_s(tid) for tid in self._task_arrival_times
        }
        starvation_count = sum(1 for w in waits.values() if w >= self.starvation_threshold_s)
        avg_wait = sum(waits.values()) / len(waits) if waits else 0.0

        longest_task = None
        if waits:
            longest_task = max(waits.items(), key=lambda item: item[1])[0]

        aging_boost_count = sum(
            1 for w in waits.values() if min(self.max_priority_boost, self.aging_factor_alpha * w) > 0.5
        )

        return FairnessMetrics(
            gini_coefficient=round(min(1.0, max(0.0, gini)), 4),
            max_min_ratio=round(max_min_ratio, 2),
            starvation_count=starvation_count,
            average_wait_time_s=round(avg_wait, 2),
            longest_waiting_task_id=longest_task,
            aging_boost_active_count=aging_boost_count,
            calculated_at=_now_utc(),
        )


default_fairness_engine = FairnessEngine()
