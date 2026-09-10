"""Simulation objectives definition and multi-objective scoring."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.simulation.schemas import SimulationObjective


class ObjectiveScore(BaseModel):
    """Evaluation score for a single objective in a simulated scenario."""

    objective_id: str
    metric: str
    target: float | None = None
    observed_in_sim: float
    satisfaction_ratio: float  # 0.0 to 1.0 (1.0 = fully satisfied or exceeded)
    is_target_met: bool


class ObjectiveEvaluator:
    """Evaluates scenario metrics against defined simulation objectives."""

    def evaluate_objective(
        self,
        objective: SimulationObjective,
        sim_metrics: dict[str, Any],
    ) -> ObjectiveScore:
        """Evaluates whether the simulation outcome satisfies the specified objective."""
        val = float(sim_metrics.get(objective.metric, 0.0))
        target = objective.target

        # Determine satisfaction
        if target is None:
            # Directional only
            satisfaction = 1.0
            is_met = True
        else:
            if "MINIMIZE" in objective.direction.upper():
                if val <= target:
                    satisfaction = 1.0
                    is_met = True
                else:
                    over = val - target
                    satisfaction = max(0.0, 1.0 - (over / (target or 1.0)))
                    is_met = False
            else:  # MAXIMIZE
                if val >= target:
                    satisfaction = 1.0
                    is_met = True
                else:
                    satisfaction = max(0.0, val / (target or 1.0))
                    is_met = False

        return ObjectiveScore(
            objective_id=objective.objective_id,
            metric=objective.metric,
            target=target,
            observed_in_sim=val,
            satisfaction_ratio=round(satisfaction, 3),
            is_target_met=is_met,
        )
