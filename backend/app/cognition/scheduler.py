"""Cognitive plan queue and fair priority scheduler for Kairo Cognitive Planning (Task 41).

Enforces:
1. Four observable queue states: QUEUED, READY, BLOCKED, RUNNING.
2. Fair scheduling with anti-starvation boost.
3. Scheduler cannot elevate privilege or bypass policy.
"""

from collections import deque
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.goals import GoalPriority
from app.cognition.plans import Plan, PlanStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


class QueueItemStatus(str, Enum):
    """Observable plan queue states."""

    QUEUED = "QUEUED"
    READY = "READY"
    BLOCKED = "BLOCKED"
    RUNNING = "RUNNING"


class QueueItem(BaseModel):
    """An item in the cognitive plan scheduling queue."""

    model_config = ConfigDict(extra="ignore")

    plan_id: str
    goal_id: str
    user_id: str
    project_id: str | None = None
    priority: GoalPriority = Field(default=GoalPriority.NORMAL)
    status: QueueItemStatus = Field(default=QueueItemStatus.QUEUED)
    enqueued_at: datetime = Field(default_factory=utc_now)
    age_seconds: float = 0.0
    starvation_boost: float = 0.0


class PlanScheduler:
    """Schedules ready plans based on priority and aging to avoid starvation."""

    def __init__(self, max_concurrent_plans: int = 4) -> None:
        self.max_concurrent_plans = max_concurrent_plans
        self._queue: dict[str, QueueItem] = {}
        self._running: set[str] = set()

    def enqueue_plan(self, plan: Plan, priority: GoalPriority = GoalPriority.NORMAL) -> QueueItem:
        """Enqueue a plan for scheduling."""
        item = QueueItem(
            plan_id=plan.plan_id,
            goal_id=plan.goal_id,
            user_id=plan.user_id,
            project_id=plan.project_id,
            priority=priority,
            status=QueueItemStatus.READY if plan.status == PlanStatus.READY else QueueItemStatus.QUEUED,
        )
        self._queue[plan.plan_id] = item
        return item

    def get_next_runnable_plan(self) -> str | None:
        """Select the next plan to run using priority + anti-starvation weighting."""
        if len(self._running) >= self.max_concurrent_plans:
            return None

        ready_candidates = [
            item for item in self._queue.values()
            if item.status == QueueItemStatus.READY and item.plan_id not in self._running
        ]
        if not ready_candidates:
            return None

        # Base priority weights
        weights = {
            GoalPriority.LOW: 1.0,
            GoalPriority.NORMAL: 2.0,
            GoalPriority.HIGH: 4.0,
            GoalPriority.CRITICAL: 10.0,
        }

        now = utc_now()
        best_item: QueueItem | None = None
        best_score = -1.0

        for item in ready_candidates:
            age = (now - item.enqueued_at).total_seconds()
            item.age_seconds = age
            # Aging anti-starvation boost: +0.1 score per 10 seconds of wait
            item.starvation_boost = round(age / 10.0 * 0.1, 2)
            score = weights.get(item.priority, 2.0) + item.starvation_boost

            if score > best_score:
                best_score = score
                best_item = item

        if best_item:
            best_item.status = QueueItemStatus.RUNNING
            self._running.add(best_item.plan_id)
            return best_item.plan_id

        return None

    def mark_completed(self, plan_id: str) -> None:
        """Mark a plan as completed and remove from running tracking."""
        self._running.discard(plan_id)
        if plan_id in self._queue:
            del self._queue[plan_id]

    def get_queue_status(self) -> dict[str, Any]:
        """Inspect queue metrics."""
        return {
            "total_queued": len(self._queue),
            "running_count": len(self._running),
            "max_concurrent": self.max_concurrent_plans,
            "items": [item.model_dump() for item in self._queue.values()],
        }
