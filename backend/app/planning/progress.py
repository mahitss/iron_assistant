"""Outcome-based and weighted strategic progress tracking (Task 58)."""

from __future__ import annotations

import logging
from typing import Any

from app.planning.schemas import (
    HealthStatus,
    MilestoneStatus,
    StrategicPlan,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Computes multidimensional progress, resisting naive task-count equivalence."""

    def compute_plan_progress(self, plan: StrategicPlan) -> dict[str, Any]:
        """Calculate holistic progress across tasks, weighted milestones, and verified desired-state criteria."""
        total_tasks = len(plan.tasks)
        completed_tasks = len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])
        blocked_tasks = len([t for t in plan.tasks if t.status == TaskStatus.BLOCKED])
        failed_tasks = len([t for t in plan.tasks if t.status == TaskStatus.FAILED])

        task_completion_pct = round((completed_tasks / max(1, total_tasks)) * 100.0, 2)

        # Milestone progress (weighted)
        total_milestones = len(plan.milestones)
        total_weight = sum(m.weight for m in plan.milestones) if plan.milestones else 0.0
        reached_weight = (
            sum(m.weight for m in plan.milestones if m.status == MilestoneStatus.REACHED and m.is_verified)
            if plan.milestones
            else 0.0
        )
        milestone_progress_pct = (
            round((reached_weight / max(0.1, total_weight)) * 100.0, 2) if total_weight > 0 else 0.0
        )

        # Desired State Invariant completion
        invariants = plan.desired_state.completion_invariants or []
        verified_criteria = plan.desired_state.verification_criteria or []
        len(invariants) + len(verified_criteria)

        # Overall composite progress favors verified milestones over simple task counts (70% milestones, 30% tasks)
        composite_progress_pct = round((milestone_progress_pct * 0.70) + (task_completion_pct * 0.30), 2)

        # Determine health
        health = plan.health
        if failed_tasks > 0:
            health = HealthStatus.AT_RISK
        if blocked_tasks > total_tasks * 0.25:
            health = HealthStatus.BLOCKED
        if composite_progress_pct >= 100.0 and (not failed_tasks and not blocked_tasks):
            health = HealthStatus.COMPLETED

        return {
            "task_count_total": total_tasks,
            "task_count_completed": completed_tasks,
            "task_count_blocked": blocked_tasks,
            "task_count_failed": failed_tasks,
            "task_completion_pct": task_completion_pct,
            "milestone_count_total": total_milestones,
            "milestone_weighted_progress_pct": milestone_progress_pct,
            "composite_progress_pct": composite_progress_pct,
            "health": health.value,
            "is_fully_completed": composite_progress_pct >= 100.0 and completed_tasks == total_tasks,
        }


progress_tracker = ProgressTracker()
