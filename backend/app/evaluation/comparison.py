"""Release regression detection and baseline delta comparison engine."""

from app.evaluation.schemas import (
    BaselineComparisonResult,
    BaselineDelta,
    BaselineMetrics,
    EvaluationRun,
    MetricSummary,
)


class RegressionDetector:
    """Evaluates evaluation results against release baselines to detect regressions."""

    # Maximum acceptable percentage drop for non-critical dimensions before warning
    TOLERANCE_THRESHOLD_PCT = 0.05

    @classmethod
    def compare(
        cls,
        current_run: EvaluationRun,
        baseline: BaselineMetrics,
        security_min: float = 1.0,
    ) -> BaselineComparisonResult:
        """Compare current run metrics against baseline and enforce release gates (Section 32 & 60)."""
        curr = current_run.metrics
        base = baseline.metrics

        deltas: list[BaselineDelta] = []
        blocking_reasons: list[str] = []

        metrics_to_compare = [
            ("security_pass_rate", curr.security_pass_rate, base.security_pass_rate, True, True),
            ("tool_selection_accuracy", curr.tool_selection_accuracy, base.tool_selection_accuracy, True, False),
            ("tool_argument_accuracy", curr.tool_argument_accuracy, base.tool_argument_accuracy, True, False),
            ("routing_accuracy", curr.routing_accuracy, base.routing_accuracy, True, False),
            ("context_precision", curr.context_precision, base.context_precision, True, False),
            ("memory_precision", curr.memory_precision, base.memory_precision, True, False),
            ("citation_groundedness", curr.citation_groundedness, base.citation_groundedness, True, False),
            ("agent_task_success", curr.agent_task_success, base.agent_task_success, True, False),
            ("overall_quality_score", curr.overall_quality_score, base.overall_quality_score, True, False),
            ("latency_p95_ms", curr.latency_p95_ms, base.latency_p95_ms, False, False),  # Lower is better
            ("estimated_cost_usd", curr.estimated_cost_usd, base.estimated_cost_usd, False, False),  # Lower is better
        ]

        for name, curr_val, base_val, higher_is_better, is_critical_security in metrics_to_compare:
            delta = curr_val - base_val
            pct = (delta / base_val) if base_val != 0 else 0.0

            if is_critical_security:
                # Security is binary invariance (Section 8 & 32): 100% required
                is_blocking = curr_val < security_min or curr_val < base_val
                status = "regressed" if delta < 0 else ("improved" if delta > 0 else "unchanged")
                if is_blocking:
                    blocking_reasons.append(
                        f"CRITICAL SECURITY REGRESSION: {name} dropped from {base_val:.2f} to {curr_val:.2f}. Release strictly blocked."
                    )
            else:
                if higher_is_better:
                    if delta < -cls.TOLERANCE_THRESHOLD_PCT:
                        status = "regressed"
                    elif delta > cls.TOLERANCE_THRESHOLD_PCT:
                        status = "improved"
                    else:
                        status = "unchanged"
                else:
                    # For latency/cost, negative delta is improvement
                    if delta > cls.TOLERANCE_THRESHOLD_PCT:
                        status = "regressed"
                    elif delta < -cls.TOLERANCE_THRESHOLD_PCT:
                        status = "improved"
                    else:
                        status = "unchanged"
                is_blocking = False

            deltas.append(
                BaselineDelta(
                    metric_name=name,
                    current_value=round(curr_val, 4),
                    baseline_value=round(base_val, 4),
                    delta=round(delta, 4),
                    delta_percentage=round(pct * 100.0, 2),
                    status=status,
                    is_blocking=is_blocking,
                )
            )

        release_blocked = len(blocking_reasons) > 0 or not current_run.security_gate_passed
        summary = (
            f"Release BLOCKED by {len(blocking_reasons)} critical security failure(s)."
            if release_blocked
            else "Quality and security gates passed. Release candidate approved."
        )

        return BaselineComparisonResult(
            current_version=current_run.kairo_version,
            baseline_version=baseline.version,
            release_blocked=release_blocked,
            security_gate_intact=len(blocking_reasons) == 0,
            deltas=deltas,
            summary=summary,
            blocking_reasons=blocking_reasons,
        )
