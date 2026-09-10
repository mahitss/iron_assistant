"""Adaptive replanning, multi-factor drift detection, and sunk cost defense (Task 58)."""

from __future__ import annotations

import logging
from typing import Any

from app.planning.schemas import (
    HealthStatus,
    StrategicPlan,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class AdaptationEngine:
    """Detects plan drift, enforces sunk cost defense, and formulates replanning proposals."""

    def evaluate_drift(
        self,
        plan: StrategicPlan,
        telemetry_update: dict[str, Any] | None = None,
        policy_modified: bool = False,
        resources_lost: list[str] | None = None,
    ) -> dict[str, Any]:
        """Assess whether reality has drifted away from plan assumptions.

        INVARIANT 16: Failed strategies must not be continued due to sunk cost.
        """
        reasons: list[str] = []
        is_replanning_required = False

        # 1. Plan Execution Drift
        failed_tasks = [t for t in plan.tasks if t.status == TaskStatus.FAILED]
        blocked_tasks = [t for t in plan.tasks if t.status == TaskStatus.BLOCKED]

        if failed_tasks:
            reasons.append(f"{len(failed_tasks)} task(s) failed during wave execution.")
            is_replanning_required = True

        if len(blocked_tasks) > len(plan.tasks) * 0.3:
            reasons.append(f"High task blockage ratio ({len(blocked_tasks)}/{len(plan.tasks)}).")
            is_replanning_required = True

        # 2. Checkpoint Variance Drift
        for cp in plan.checkpoints:
            if cp.decision_action in ("REPLAN", "ROLLBACK"):
                reasons.append(f"Checkpoint '{cp.name}' triggered {cp.decision_action} with variance {cp.variance_score}.")
                is_replanning_required = True

        # 3. Environment & Policy Drift
        if policy_modified:
            reasons.append("Security or organizational policy was modified since plan inception.")
            is_replanning_required = True

        if resources_lost:
            reasons.append(f"Crucial resources became unavailable: {resources_lost}")
            is_replanning_required = True

        # 4. Sunk Cost Defense: Calculate forward expected value
        completed_count = len([t for t in plan.tasks if t.status == TaskStatus.COMPLETED])
        sunk_cost_warning = False
        if completed_count > len(plan.tasks) * 0.5 and is_replanning_required:
            sunk_cost_warning = True
            reasons.append(
                "SUNK COST DEFENSE ACTIVATED: Despite significant prior task completions, "
                "forward expected value of the current trajectory is negative or compromised. "
                "Replanning recommended over blind continuation."
            )

        new_health = HealthStatus.ON_TRACK
        if is_replanning_required:
            new_health = HealthStatus.REPLANNING_REQUIRED
        elif blocked_tasks:
            new_health = HealthStatus.BLOCKED
        elif failed_tasks:
            new_health = HealthStatus.AT_RISK

        return {
            "is_replanning_required": is_replanning_required,
            "health": new_health,
            "reasons": reasons,
            "sunk_cost_defense_triggered": sunk_cost_warning,
            "failed_tasks": [t.task_id for t in failed_tasks],
            "blocked_tasks": [t.task_id for t in blocked_tasks],
        }

    def generate_replanning_proposal(
        self,
        plan: StrategicPlan,
        drift_analysis: dict[str, Any],
        actor: str = "SYSTEM_REPLANNER",
    ) -> dict[str, Any]:
        """Formulate structured adaptation proposal without silently mutating history."""
        return {
            "plan_id": plan.plan_id,
            "original_version": plan.version,
            "proposed_version": plan.version + 1,
            "actor": actor,
            "trigger_reasons": drift_analysis.get("reasons", []),
            "strategic_recommendations": [
                "Re-sequence unresolved tasks to bypass blocked paths.",
                "De-escalate non-critical milestones to preserve hard delivery deadlines.",
                "Revalidate resource allocations against updated environment.",
            ],
            "approval_required": True,
        }


adaptation_engine = AdaptationEngine()
