"""Multi-objective Pareto optimization and Goodhart's Law defenses (Task 62)."""

from __future__ import annotations

import logging

from app.optimization.schemas import (
    ObjectiveDirection,
    OptimizationObjective,
    OptimizationRecommendation,
)

logger = logging.getLogger(__name__)


class MultiObjectiveOptimizer:
    """Computes Pareto dominance frontiers and detects metric gaming (Goodhart's Law).

    Invariant 5 & 16: When a metric becomes a target, it ceases to be a good measure.
    The optimizer detects and suppresses measurement manipulation and balances tradeoffs across Pareto fronts.
    """

    def __init__(self) -> None:
        self._objectives: dict[str, OptimizationObjective] = {}
        self._register_default_objectives()

    def _register_default_objectives(self) -> None:
        """Seed canonical optimization objectives."""
        defaults = [
            OptimizationObjective(
                objective_id="obj_latency",
                name="Minimize Request Latency",
                metric_name="latency_ms",
                direction=ObjectiveDirection.MINIMIZE,
                weight=1.0,
            ),
            OptimizationObjective(
                objective_id="obj_cost",
                name="Minimize Infrastructure Cost",
                metric_name="cost_usd",
                direction=ObjectiveDirection.MINIMIZE,
                weight=0.8,
            ),
            OptimizationObjective(
                objective_id="obj_reliability",
                name="Maximize Verification Success Rate",
                metric_name="verification_success_rate",
                direction=ObjectiveDirection.MAXIMIZE,
                weight=1.2,
            ),
            OptimizationObjective(
                objective_id="obj_throughput",
                name="Maximize Request Throughput",
                metric_name="throughput_rps",
                direction=ObjectiveDirection.MAXIMIZE,
                weight=0.6,
            ),
        ]
        for obj in defaults:
            self._objectives[obj.objective_id] = obj

    def list_objectives(self) -> list[OptimizationObjective]:
        """List active optimization objectives."""
        return list(self._objectives.values())

    def compute_composite_score(
        self,
        predicted_deltas: dict[str, float],  # positive means improvement in metric's desired direction
    ) -> float:
        """Compute weighted utility score across multiple objectives."""
        total_score = 0.0
        total_weight = 0.0
        for obj in self._objectives.values():
            delta = predicted_deltas.get(obj.metric_name, 0.0)
            score = delta if obj.direction == ObjectiveDirection.MAXIMIZE else -delta
            total_score += score * obj.weight
            total_weight += obj.weight

        if total_weight <= 0:
            return 0.0
        return round(total_score / total_weight, 4)

    def is_pareto_dominant(
        self,
        candidate_metrics: dict[str, float],
        competitor_metrics: dict[str, float],
    ) -> bool:
        """Evaluate if candidate strictly Pareto-dominates competitor.

        A candidate dominates if it is at least as good in all objectives and strictly better in at least one.
        """
        at_least_as_good_in_all = True
        strictly_better_in_one = False

        for obj in self._objectives.values():
            cand_val = candidate_metrics.get(obj.metric_name)
            comp_val = competitor_metrics.get(obj.metric_name)
            if cand_val is None or comp_val is None:
                continue

            if obj.direction == ObjectiveDirection.MINIMIZE:
                if cand_val > comp_val:  # candidate is worse
                    at_least_as_good_in_all = False
                    break
                if cand_val < comp_val:  # candidate is better
                    strictly_better_in_one = True
            else:  # MAXIMIZE
                if cand_val < comp_val:  # candidate is worse
                    at_least_as_good_in_all = False
                    break
                if cand_val > comp_val:  # candidate is better
                    strictly_better_in_one = True

        return at_least_as_good_in_all and strictly_better_in_one

    def detect_goodharts_gaming(
        self,
        recommendation: OptimizationRecommendation,
        simulated_metrics: dict[str, float],
    ) -> tuple[bool, str | None]:
        """Check for metric gaming, proxy manipulation, or measurement suppression.

        Examples:
        - Latency improved by dropping verification.
        - Error rate improved by suppressing failure reports.
        - Cost improved by turning off security probes.
        """
        # 1. Gaming latency by weakening verification
        target = recommendation.target_parameter.lower()
        if "timeout" in target or "latency" in target:
            verif_rate = simulated_metrics.get("verification_success_rate", 1.0)
            if verif_rate < 0.95:
                return (
                    True,
                    "GOODHARTS_LAW_VIOLATION: Latency optimization causes regression in verification success rate.",
                )

        # 2. Gaming cost by starving essential resources
        if "cost" in target or "cache" in target:
            err_rate = simulated_metrics.get("error_rate", 0.0)
            if err_rate > 0.04:
                return (
                    True,
                    "GOODHARTS_LAW_VIOLATION: Cost optimization induces significant error rate spike.",
                )

        return False, None


multi_objective_optimizer = MultiObjectiveOptimizer()
