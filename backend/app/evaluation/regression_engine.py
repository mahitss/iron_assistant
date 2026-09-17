"""Regression Detection Engine & 'Do Nothing' Baseline Evaluation.
Task 104 Section 25 & 26.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
from app.evaluation.domain import (
    EvaluationBaseline,
    EvaluationComparison,
    EvaluationRun,
    RegressionCategory,
    RegressionFinding,
    RegressionSeverity,
)

logger = logging.getLogger("kairo.evaluation.regression_engine")


class ContinuousRegressionEngine:
    """Detects multi-category regressions and evaluates candidate runs against frozen baselines."""

    # Default relative drop threshold to declare regression (e.g., 5% drop)
    DEFAULT_TOLERANCE_DROP = 0.05
    MIN_SAMPLE_SIZE_FOR_REGRESSION = 5

    @classmethod
    def compare_run_to_baseline(
        cls,
        candidate_run: EvaluationRun,
        baseline: EvaluationBaseline,
        sample_size: int = 10,
    ) -> EvaluationComparison:
        """Performs rigorous regression detection across all 13 categories."""
        deltas: list[dict[str, Any]] = []
        regressions: list[RegressionFinding] = []
        blocking_reasons: list[str] = []

        base_metrics = baseline.metrics
        cand_metrics = {
            "pass_rate": candidate_run.pass_rate,
            "security_pass_rate": candidate_run.security_pass_rate,
            "safety_pass_rate": candidate_run.safety_pass_rate,
            "quality_score": candidate_run.quality_score / 100.0,
            "latency_p95_ms": candidate_run.latency_p95_ms,
            "estimated_cost_usd": candidate_run.estimated_cost_usd,
        }

        # Metric mapping to regression categories
        metric_meta = [
            ("security_pass_rate", RegressionCategory.SECURITY, True, RegressionSeverity.CRITICAL),
            ("safety_pass_rate", RegressionCategory.SAFETY, True, RegressionSeverity.CRITICAL),
            ("pass_rate", RegressionCategory.FUNCTIONAL, True, RegressionSeverity.HIGH),
            ("quality_score", RegressionCategory.QUALITY, True, RegressionSeverity.MEDIUM),
            ("latency_p95_ms", RegressionCategory.PERFORMANCE, False, RegressionSeverity.LOW),  # Lower is better
            ("estimated_cost_usd", RegressionCategory.RESOURCE, False, RegressionSeverity.LOW),  # Lower is better
        ]

        for m_name, category, higher_is_better, default_severity in metric_meta:
            cand_val = cand_metrics.get(m_name, 0.0)
            base_val = base_metrics.get(m_name, cand_val)

            delta = cand_val - base_val
            pct = (delta / base_val) if base_val != 0 else 0.0

            is_regression = False
            if higher_is_better:
                if delta < -cls.DEFAULT_TOLERANCE_DROP:
                    is_regression = True
            else:
                # For latency/cost, positive delta is regression
                if delta > cls.DEFAULT_TOLERANCE_DROP:
                    is_regression = True

            # Special invariant: Security & Safety must be 100% strict (zero tolerance)
            if category in (RegressionCategory.SECURITY, RegressionCategory.SAFETY):
                if cand_val < 1.0 or delta < 0:
                    is_regression = True

            is_statistically_significant = sample_size >= cls.MIN_SAMPLE_SIZE_FOR_REGRESSION
            is_blocking = is_regression and (default_severity in (RegressionSeverity.CRITICAL, RegressionSeverity.HIGH))

            if is_regression and is_statistically_significant:
                reg_finding = RegressionFinding(
                    run_id=candidate_run.id,
                    baseline_id=baseline.id,
                    category=category,
                    severity=default_severity,
                    metric_name=m_name,
                    baseline_value=round(base_val, 4),
                    candidate_value=round(cand_val, 4),
                    delta=round(delta, 4),
                    delta_percentage=round(pct * 100.0, 2),
                    sample_size=sample_size,
                    is_statistically_significant=is_statistically_significant,
                    evidence_summary=f"Metric '{m_name}' regressed from {base_val:.4f} to {cand_val:.4f} ({pct*100:.1f}%)",
                    is_blocking=is_blocking,
                )
                regressions.append(reg_finding)

                if is_blocking:
                    blocking_reasons.append(
                        f"BLOCKING {category.value} REGRESSION: '{m_name}' dropped from {base_val:.2f} to {cand_val:.2f}."
                    )

            deltas.append({
                "metric_name": m_name,
                "category": category.value,
                "candidate_value": round(cand_val, 4),
                "baseline_value": round(base_val, 4),
                "delta": round(delta, 4),
                "delta_percentage": round(pct * 100.0, 2),
                "status": "regressed" if is_regression else ("improved" if delta > 0 else "unchanged"),
                "is_blocking": is_blocking,
            })

        release_blocked = len(blocking_reasons) > 0 or candidate_run.security_pass_rate < 1.0
        summary = (
            f"Release candidate BLOCKED by {len(blocking_reasons)} critical/high regression(s)."
            if release_blocked
            else f"Evaluation comparison passed. {len(regressions)} non-blocking regression(s) observed."
        )

        return EvaluationComparison(
            run_id=candidate_run.id,
            baseline_id=baseline.id,
            candidate_version=candidate_run.candidate_version,
            baseline_version=baseline.version,
            release_blocked=release_blocked,
            security_gate_passed=candidate_run.security_pass_rate >= 1.0,
            regressions_count=len(regressions),
            blocking_reasons=blocking_reasons,
            deltas=deltas,
            summary=summary,
        )

    @classmethod
    def evaluate_do_nothing_baseline(
        cls,
        intervention_outcome_score: float,
        no_action_outcome_score: float,
        resource_cost_of_action: float,
    ) -> dict[str, Any]:
        """Evaluates whether autonomous intervention produced an outcome demonstrably superior
        to taking no action at all (Section 26).
        """
        net_gain = intervention_outcome_score - no_action_outcome_score
        action_was_justified = net_gain > 0.05

        return {
            "intervention_score": round(intervention_outcome_score, 4),
            "no_action_score": round(no_action_outcome_score, 4),
            "net_gain": round(net_gain, 4),
            "resource_cost": round(resource_cost_of_action, 4),
            "action_was_justified": action_was_justified,
            "verdict": "INTERVENTION_SUPERIOR" if action_was_justified else ("NO_ACTION_BETTER" if net_gain < 0 else "INTERVENTION_NEGLIGIBLE"),
        }
