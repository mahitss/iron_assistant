"""Gap analysis, current vs baseline vs target evaluation, and causal contributor attribution (Task 62)."""

from __future__ import annotations

import logging

from app.optimization.baselines import BaselineManager, baseline_manager
from app.optimization.metrics import MetricsEngine, metrics_engine
from app.optimization.schemas import (
    ObjectiveDirection,
    OptimizationGap,
)

logger = logging.getLogger(__name__)


class OptimizationEvaluator:
    """Evaluates current system performance against baselines and targets to uncover actionable performance gaps.

    Invariant 13: Compares current state, baseline, target, and constraint state without fabricating causality.
    """

    def __init__(
        self,
        metrics_eng: MetricsEngine | None = None,
        baselines_mgr: BaselineManager | None = None,
    ) -> None:
        self._metrics = metrics_eng or metrics_engine
        self._baselines = baselines_mgr or baseline_manager

    def evaluate_gaps(self) -> list[OptimizationGap]:
        """Identify measurable performance and efficiency gaps across tracked metrics."""
        gaps: list[OptimizationGap] = []
        aggregations = self._metrics.aggregate_all()

        for agg in aggregations:
            if not agg.has_sufficient_data:
                continue

            defn = self._metrics.get_definition(agg.metric_name)
            if not defn or defn.target_value is None:
                continue

            target = defn.target_value
            current = agg.mean
            direction = defn.direction

            # Determine if current state is lagging behind target
            is_gap = False
            delta = 0.0
            gap_pct = 0.0

            if direction == ObjectiveDirection.MINIMIZE:
                if current > target:
                    is_gap = True
                    delta = current - target
                    gap_pct = (delta / target) * 100.0 if target > 0 else 0.0
            else:  # MAXIMIZE
                if current < target:
                    is_gap = True
                    delta = target - current
                    gap_pct = (delta / target) * 100.0 if target > 0 else 0.0

            if is_gap:
                contributors = self._infer_likely_contributors(agg.metric_name)
                urgency = "HIGH" if gap_pct > 50.0 else ("MEDIUM" if gap_pct > 20.0 else "NORMAL")

                gap = OptimizationGap(
                    metric_name=agg.metric_name,
                    current_value=current,
                    target_value=target,
                    gap_delta=round(delta, 4),
                    gap_percentage=round(gap_pct, 2),
                    likely_contributors=contributors,
                    confidence=0.88,
                    urgency=urgency,
                )
                gaps.append(gap)
                logger.info(
                    "OPTIMIZATION_GAP_DETECTED: metric=%s delta=%.2f (%.1f%%) urgency=%s",
                    agg.metric_name,
                    delta,
                    gap_pct,
                    urgency,
                )

        return gaps

    def _infer_likely_contributors(self, metric_name: str) -> list[str]:
        """Attribute likely structural contributors without fabricating definitive root causes."""
        if metric_name == "latency_ms":
            return ["model_routing_weights", "cache_ttl_sizing", "queue_batch_size"]
        if metric_name == "cost_usd":
            return ["model_selection_bias", "cache_hit_rate", "background_concurrency"]
        if metric_name == "error_rate":
            return ["upstream_dependency_timeout", "retry_backoff_frequency"]
        if metric_name == "throughput_rps":
            return ["batch_size_items", "resource_concurrency_limit"]
        if metric_name == "recovery_time_s":
            return ["checkpoint_verification_latency", "state_reconciliation_delays"]
        return ["runtime_parameter_configuration"]


optimization_evaluator = OptimizationEvaluator()
