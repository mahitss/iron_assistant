"""Multi-dimensional continuous learning evaluation without single gameable reward (INVARIANTS 151-156)."""

from __future__ import annotations

from typing import Any
from app.learning.schemas import ContinuousLearningMetricsSchema


class ContinuousLearningEvaluator:
    """Tracks multi-dimensional operational metrics and prevents metric gaming/reward hacking."""

    def __init__(self) -> None:
        self.metrics = ContinuousLearningMetricsSchema()
        self._samples: int = 0
        self._successes: int = 0
        self._verification_attempts: int = 0
        self._verification_passes: int = 0

    def record_execution(
        self,
        was_successful: bool,
        was_verified: bool,
        safety_violation: bool = False,
        latency_ms: float = 0.0,
        cost: float = 0.0,
        user_rating: float | None = None,
    ) -> None:
        """INVARIANT 152: Records multi-dimensional execution outcome."""
        self._samples += 1
        if was_successful:
            self._successes += 1
        self.metrics.accuracy = round(self._successes / self._samples, 3)

        self._verification_attempts += 1
        if was_verified:
            self._verification_passes += 1
        self.metrics.verification_rate = round(self._verification_passes / self._verification_attempts, 3)

        if safety_violation:
            self.metrics.safety_violations += 1

        if user_rating is not None:
            # User satisfaction is weighted between 0.0 and 1.0
            norm_rating = min(max(user_rating / 5.0, 0.0), 1.0)
            self.metrics.user_satisfaction = round(
                (self.metrics.user_satisfaction * 0.9) + (norm_rating * 0.1),
                3
            )

        self.metrics.latency_ms = round(latency_ms, 2)
        self.metrics.cost_savings = round(self.metrics.cost_savings + cost, 4)

    def evaluate_adaptation_safety(self, candidate_metrics: dict[str, Any]) -> bool:
        """INVARIANT 156: Safety metrics cannot be traded away for task completion.
        Rejects candidates that lower verification rate or introduce safety violations.
        """
        if candidate_metrics.get("safety_violations", 0) > 0:
            return False
        if candidate_metrics.get("verification_rate", 1.0) < 0.8:
            return False
        return True

    def calculate_multi_dimensional_score(
        self,
        accuracy: float,
        safety_score: float,
        verification_coverage: float,
        latency_score: float = 0.5,
        cost_score: float = 0.5,
        user_satisfaction: float = 0.5,
    ) -> float:
        """INVARIANT 151-153: Balanced multi-factor evaluation preventing single reward gaming.
        Heavily penalizes safety compromises and lack of verification.
        """
        # If safety or verification is severely degraded, the overall score drops precipitously
        if safety_score < 0.8:
            return round(safety_score * 0.4, 3)
        if verification_coverage < 0.5:
            return round(verification_coverage * 0.5, 3)

        composite = (
            accuracy * 0.25
            + safety_score * 0.35
            + verification_coverage * 0.25
            + latency_score * 0.05
            + cost_score * 0.05
            + user_satisfaction * 0.05
        )
        return round(composite, 3)

    def get_metrics_report(self) -> dict[str, Any]:
        """INVARIANT 151: Returns separate dimensions, preventing single-score gaming."""
        return {
            "accuracy": self.metrics.accuracy,
            "safety_violations": self.metrics.safety_violations,
            "verification_rate": self.metrics.verification_rate,
            "user_satisfaction": self.metrics.user_satisfaction,
            "cost_savings": self.metrics.cost_savings,
            "latency_ms": self.metrics.latency_ms,
            "tool_reliability": self.metrics.tool_reliability,
            "total_experiences": self.metrics.total_experiences,
            "total_lessons": self.metrics.total_lessons,
            "promoted_workflows": self.metrics.promoted_workflows,
            "total_workflows": self.metrics.promoted_workflows,
            "active_heuristics": self.metrics.active_heuristics,
            "total_heuristics": self.metrics.active_heuristics,
        }
