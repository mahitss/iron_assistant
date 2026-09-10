"""Outcome recording, estimation calibration, and strategy performance learning (Task 58)."""

from __future__ import annotations

import logging
from typing import Any

from app.planning.schemas import PlanOutcome, StrategicPlan

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """Tracks post-execution outcomes, calibers future estimations, and logs strategy performance."""

    def __init__(self) -> None:
        self._strategy_history: list[dict[str, Any]] = []
        self._duration_calibration_samples: list[float] = []

    def record_plan_outcome(
        self,
        plan: StrategicPlan,
        success: bool,
        actual_duration_hours: float,
        actual_cost: float = 0.0,
        lessons_learned: list[str] | None = None,
    ) -> PlanOutcome:
        """Record the post-execution outcome of a strategic plan and calibrate learning."""
        total_estimated_hours = sum(t.duration_expected for t in plan.tasks)
        est_err = 0.0
        if total_estimated_hours > 0:
            est_err = round((actual_duration_hours - total_estimated_hours) / total_estimated_hours, 3)

        outcome = PlanOutcome(
            plan_id=plan.plan_id,
            success=success,
            actual_duration=round(actual_duration_hours, 2),
            actual_cost=round(actual_cost, 2),
            estimation_error=est_err,
            lessons_learned=lessons_learned or [],
        )

        # Update learning telemetry
        self._strategy_history.append({
            "plan_id": plan.plan_id,
            "strategy_type": plan.strategy.strategy_type.value,
            "strategy_name": plan.strategy.name,
            "success": success,
            "complexity": plan.strategy.estimated_complexity,
            "estimation_error": est_err,
        })

        if total_estimated_hours > 0:
            # Ratio of actual / estimated
            ratio = actual_duration_hours / total_estimated_hours
            self._duration_calibration_samples.append(ratio)

        logger.info(
            "Plan %s outcome recorded (success=%s, estimation_error=%s).",
            plan.plan_id,
            success,
            est_err,
        )
        return outcome

    def get_calibration_factor(self) -> float:
        """Return rolling average duration calibration factor (default 1.0)."""
        if not self._duration_calibration_samples:
            return 1.0
        return round(sum(self._duration_calibration_samples) / len(self._duration_calibration_samples), 2)

    def get_strategy_performance_stats(self) -> dict[str, Any]:
        """Aggregate performance and success rates for strategy archetypes."""
        stats: dict[str, dict[str, Any]] = {}
        for entry in self._strategy_history:
            stype = entry["strategy_type"]
            if stype not in stats:
                stats[stype] = {"total": 0, "successful": 0, "success_rate": 0.0}
            stats[stype]["total"] += 1
            if entry["success"]:
                stats[stype]["successful"] += 1
            stats[stype]["success_rate"] = round(stats[stype]["successful"] / stats[stype]["total"], 2)
        return stats


outcome_tracker = OutcomeTracker()
