"""Pareto optimization and multi-objective trade-off analysis across candidate scenarios."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.simulation.schemas import SimulationObjective


class ParetoComparisonResult(BaseModel):
    """Result of Pareto-frontier analysis across evaluated simulation scenarios."""

    pareto_optimal_scenario_ids: list[str] = Field(default_factory=list)
    dominated_scenario_ids: list[str] = Field(default_factory=list)
    trade_off_explanations: list[str] = Field(default_factory=list)
    recommended_candidates: list[str] = Field(default_factory=list)
    has_conflicting_objectives: bool = False


class ParetoOptimizer:
    """Computes Pareto dominance across multiple simulation scenario metrics."""

    def find_pareto_frontier(
        self,
        scenario_metrics: dict[str, dict[str, float]],
        objectives: list[SimulationObjective],
    ) -> ParetoComparisonResult:
        """Finds non-dominated (Pareto-optimal) scenarios given multi-dimensional objectives."""
        scenario_ids = list(scenario_metrics.keys())
        if not scenario_ids:
            return ParetoComparisonResult()

        dominated: set[str] = set()
        explanations: list[str] = []

        for id_a in scenario_ids:
            metrics_a = scenario_metrics[id_a]
            for id_b in scenario_ids:
                if id_a == id_b:
                    continue
                metrics_b = scenario_metrics[id_b]

                # Check if A strictly dominates B:
                # A is better or equal in ALL objectives, and strictly better in at least ONE
                better_in_all = True
                strictly_better_in_one = False

                for obj in objectives:
                    m = obj.metric
                    val_a = metrics_a.get(m, 0.0)
                    val_b = metrics_b.get(m, 0.0)

                    if "MINIMIZE" in obj.direction.upper():
                        if val_a > val_b:
                            better_in_all = False
                            break
                        elif val_a < val_b:
                            strictly_better_in_one = True
                    else:  # MAXIMIZE
                        if val_a < val_b:
                            better_in_all = False
                            break
                        elif val_a > val_b:
                            strictly_better_in_one = True

                if better_in_all and strictly_better_in_one:
                    dominated.add(id_b)
                    explanations.append(
                        f"Scenario '{id_a}' dominates '{id_b}' across evaluated objectives."
                    )

        pareto_optimal = [s_id for s_id in scenario_ids if s_id not in dominated]
        conflicts = len(pareto_optimal) > 1

        if conflicts:
            explanations.append(
                f"Multi-objective trade-off detected: {len(pareto_optimal)} Pareto-optimal scenarios identified. "
                "No single optimum can be selected without subjective preference weighting."
            )

        return ParetoComparisonResult(
            pareto_optimal_scenario_ids=pareto_optimal,
            dominated_scenario_ids=list(dominated),
            trade_off_explanations=explanations,
            recommended_candidates=pareto_optimal,
            has_conflicting_objectives=conflicts,
        )
