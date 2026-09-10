"""Recommendation generator synthesizing bounded parameter tuning proposals (Task 62)."""

from __future__ import annotations

import logging

from app.optimization.constraints import ConstraintValidator, constraint_validator
from app.optimization.parameters import AdjustableParameterRegistry, adjustable_parameter_registry
from app.optimization.schemas import (
    OptimizationGap,
    OptimizationRecommendation,
    RecommendationType,
    RiskLevel,
)

logger = logging.getLogger(__name__)


class RecommendationGenerator:
    """Synthesizes bounded, risk-graded optimization recommendations from identified operational gaps.

    Invariant 14 & 35: Recommendations are proposals, not execution. Every recommendation defines
    an explicit rollback plan and must pass constraint validation and approval gates.
    """

    def __init__(
        self,
        registry: AdjustableParameterRegistry | None = None,
        validator: ConstraintValidator | None = None,
    ) -> None:
        self._registry = registry or adjustable_parameter_registry
        self._validator = validator or constraint_validator

    def generate_recommendations(
        self,
        gaps: list[OptimizationGap],
        current_metrics: dict[str, float] | None = None,
    ) -> list[OptimizationRecommendation]:
        """Generate candidate parameter modifications to close observed operational gaps."""
        candidates: list[OptimizationRecommendation] = []

        for gap in gaps:
            if gap.metric_name == "latency_ms":
                candidates.extend(self._recommend_for_latency(gap))
            elif gap.metric_name == "cost_usd":
                candidates.extend(self._recommend_for_cost(gap))
            elif gap.metric_name == "error_rate":
                candidates.extend(self._recommend_for_error_rate(gap))
            elif gap.metric_name == "throughput_rps":
                candidates.extend(self._recommend_for_throughput(gap))

        # Validate candidates against hard constraints
        approved_candidates: list[OptimizationRecommendation] = []
        for cand in candidates:
            is_valid, _ = self._validator.validate_recommendation(cand, current_metrics=current_metrics)
            if is_valid:
                approved_candidates.append(cand)

        return approved_candidates

    def _recommend_for_latency(self, gap: OptimizationGap) -> list[OptimizationRecommendation]:
        recs: list[OptimizationRecommendation] = []

        # Candidate 1: Increase model routing latency weight
        param = self._registry.get_parameter("model_routing_latency_weight")
        if param:
            proposed = min(param.maximum, param.current_value + param.max_step_change)
            if proposed > param.current_value:
                recs.append(
                    OptimizationRecommendation(
                        recommendation_type=RecommendationType.CHANGE_MODEL_ROUTING,
                        title="Prioritize Faster Model Engines in Router",
                        description=f"Increase latency preference weight from {param.current_value:.2f} to {proposed:.2f} to reduce tail latency.",
                        target_parameter=param.parameter_name,
                        current_value=param.current_value,
                        proposed_value=round(proposed, 2),
                        expected_benefit=f"Projected latency reduction of ~{min(gap.gap_percentage * 0.4, 25.0):.1f}%",
                        expected_cost="Slight increase in token cost",
                        risk=param.risk_level,
                        requires_approval=param.requires_approval,
                        rollback_strategy=f"Restore {param.parameter_name} to {param.current_value}",
                        confidence=0.88,
                    )
                )

        # Candidate 2: Expand cache partition
        param_cache = self._registry.get_parameter("cache_max_size_mb")
        if param_cache:
            proposed_cache = min(param_cache.maximum, param_cache.current_value + param_cache.max_step_change)
            if proposed_cache > param_cache.current_value:
                recs.append(
                    OptimizationRecommendation(
                        recommendation_type=RecommendationType.ADJUST_CACHE,
                        title="Expand Cache Capacity to Improve Hit Rate",
                        description=f"Increase cache memory limit from {param_cache.current_value:.0f}MB to {proposed_cache:.0f}MB.",
                        target_parameter=param_cache.parameter_name,
                        current_value=param_cache.current_value,
                        proposed_value=round(proposed_cache, 0),
                        expected_benefit="Reduces cache misses and accelerates repeated lookups",
                        expected_cost="Increases memory consumption by 128MB",
                        risk=RiskLevel.LOW,
                        requires_approval=False,
                        rollback_strategy=f"Restore {param_cache.parameter_name} to {param_cache.current_value}",
                        confidence=0.92,
                    )
                )

        return recs

    def _recommend_for_cost(self, gap: OptimizationGap) -> list[OptimizationRecommendation]:
        recs: list[OptimizationRecommendation] = []
        param = self._registry.get_parameter("model_routing_cost_weight")
        if param:
            proposed = min(param.maximum, param.current_value + param.max_step_change)
            if proposed > param.current_value:
                recs.append(
                    OptimizationRecommendation(
                        recommendation_type=RecommendationType.CHANGE_MODEL_ROUTING,
                        title="Incentivize Cost-Efficient Models in Router",
                        description=f"Increase cost optimization preference from {param.current_value:.2f} to {proposed:.2f}.",
                        target_parameter=param.parameter_name,
                        current_value=param.current_value,
                        proposed_value=round(proposed, 2),
                        expected_benefit="Reduces hourly inference expenditure",
                        expected_cost="Potential mild increase in p95 latency",
                        risk=param.risk_level,
                        requires_approval=param.requires_approval,
                        rollback_strategy=f"Restore {param.parameter_name} to {param.current_value}",
                        confidence=0.85,
                    )
                )
        return recs

    def _recommend_for_error_rate(self, gap: OptimizationGap) -> list[OptimizationRecommendation]:
        recs: list[OptimizationRecommendation] = []
        param = self._registry.get_parameter("retry_backoff_base_seconds")
        if param:
            proposed = min(param.maximum, param.current_value + param.max_step_change)
            if proposed > param.current_value:
                recs.append(
                    OptimizationRecommendation(
                        recommendation_type=RecommendationType.ADJUST_TIMEOUT,
                        title="Increase Retry Backoff Delay to Prevent Cascades",
                        description=f"Lengthen retry backoff from {param.current_value:.1f}s to {proposed:.1f}s.",
                        target_parameter=param.parameter_name,
                        current_value=param.current_value,
                        proposed_value=round(proposed, 1),
                        expected_benefit="Dampens retry storms during upstream saturation",
                        expected_cost="Minor delay on failed operations",
                        risk=RiskLevel.LOW,
                        requires_approval=False,
                        rollback_strategy=f"Restore {param.parameter_name} to {param.current_value}",
                        confidence=0.89,
                    )
                )
        return recs

    def _recommend_for_throughput(self, gap: OptimizationGap) -> list[OptimizationRecommendation]:
        recs: list[OptimizationRecommendation] = []
        param = self._registry.get_parameter("batch_size_items")
        if param:
            proposed = min(param.maximum, param.current_value + param.max_step_change)
            if proposed > param.current_value:
                recs.append(
                    OptimizationRecommendation(
                        recommendation_type=RecommendationType.ADJUST_BATCHING,
                        title="Increase Asynchronous Batch Processing Capacity",
                        description=f"Scale batch size from {param.current_value:.0f} to {proposed:.0f} items.",
                        target_parameter=param.parameter_name,
                        current_value=param.current_value,
                        proposed_value=round(proposed, 0),
                        expected_benefit="Increases ingestion throughput and reduces per-item overhead",
                        expected_cost="Marginal buffer memory usage",
                        risk=RiskLevel.LOW,
                        requires_approval=False,
                        rollback_strategy=f"Restore {param.parameter_name} to {param.current_value}",
                        confidence=0.91,
                    )
                )
        return recs


recommendation_generator = RecommendationGenerator()
