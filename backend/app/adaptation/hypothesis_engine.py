"""Hypothesis formulation, validation, and falsification engine for Task 105.
Enforces strict IF-THEN-BECAUSE structure and measurability.
Rejects vague assertions without quantifiable criteria.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional
import uuid

from app.adaptation.domain import AdaptationHypothesis

logger = logging.getLogger("kairo.adaptation.hypothesis")


class HypothesisEngine:
    """Manages the creation, validation, counter-formulation, and falsification of adaptation hypotheses."""

    def __init__(self) -> None:
        self.hypotheses: dict[str, AdaptationHypothesis] = {}

    def form_hypothesis(
        self,
        condition_change: str,
        expected_outcome: str,
        evidence_reasoning: str,
        confidence: float = 0.5,
        measurable_outcomes: Optional[dict[str, float]] = None,
        falsification_criteria: Optional[list[str]] = None,
        assumptions: Optional[list[str]] = None,
        counter_hypotheses: Optional[list[str]] = None,
        evidence_references: Optional[list[str]] = None,
        originating_finding_id: Optional[str] = None,
    ) -> AdaptationHypothesis:
        """Constructs and validates a formal hypothesis. Raises ValueError if vague or non-measurable."""
        hyp = AdaptationHypothesis(
            condition_change=condition_change.strip(),
            expected_outcome=expected_outcome.strip(),
            evidence_reasoning=evidence_reasoning.strip(),
            confidence=max(0.0, min(1.0, confidence)),
            measurable_outcomes=measurable_outcomes or {},
            falsification_criteria=falsification_criteria or [],
            assumptions=assumptions or [],
            counter_hypotheses=counter_hypotheses or [],
            evidence_references=evidence_references or [],
            originating_finding_id=originating_finding_id,
            created_at=datetime.now(UTC),
        )

        valid, reason = hyp.validate_measurability()
        if not valid:
            logger.warning("Hypothesis rejected: %s", reason)
            raise ValueError(f"Invalid hypothesis: {reason}")

        # Auto-generate counter-hypothesis if none provided
        if not hyp.counter_hypotheses:
            hyp.counter_hypotheses.append(
                f"Null Hypothesis: Applying '{hyp.condition_change[:40]}...' produces no statistically significant difference over baseline."
            )

        self.hypotheses[hyp.id] = hyp
        logger.info("Formulated valid hypothesis: %s (confidence=%.2f)", hyp.id, hyp.confidence)
        return hyp

    def synthesize_from_regression_finding(
        self,
        finding_id: str,
        metric_name: str,
        baseline_val: float,
        measured_val: float,
        affected_capabilities: list[str],
        suggested_intervention: Optional[str] = None,
    ) -> AdaptationHypothesis:
        """Synthesizes a structured, falsifiable hypothesis from a Task 104 continuous evaluation regression finding."""
        delta = baseline_val - measured_val
        cap_str = ", ".join(affected_capabilities) if affected_capabilities else "target capability"

        intervention = suggested_intervention or f"adjust parameter configuration and retry policy for {cap_str}"
        condition = f"If {intervention} is applied to {cap_str}"
        expected = f"then {metric_name} will recover by at least {abs(delta):.3f} without degrading latency beyond 10%"
        because = f"Task 104 regression finding {finding_id} demonstrated a regression from baseline {baseline_val:.2f} to {measured_val:.2f} (delta={delta:+.3f})"

        return self.form_hypothesis(
            condition_change=condition,
            expected_outcome=expected,
            evidence_reasoning=because,
            confidence=0.75,
            measurable_outcomes={
                metric_name: abs(delta),
                "max_latency_regression_pct": 10.0,
            },
            falsification_criteria=[
                f"{metric_name} does not improve by at least {abs(delta) * 0.5:.3f}",
                "Safety or security violations are observed during test execution",
                "Execution error rate increases by more than 2%",
            ],
            assumptions=[
                "The regression is caused by parameter misconfiguration rather than underlying model degradation",
                "Resource capacity is sufficient to sustain baseline throughput",
            ],
            originating_finding_id=finding_id,
        )

    def evaluate_falsification(
        self,
        hypothesis: AdaptationHypothesis,
        measured_metrics: dict[str, float],
        safety_breached: bool = False,
        error_rate_delta: float = 0.0,
    ) -> tuple[bool, str]:
        """Evaluates whether the experiment results falsify the hypothesis.
        Returns: (is_falsified, rationale)
        """
        if safety_breached:
            return True, "Falsified: A safety or security constraint was breached during the experiment."

        if error_rate_delta > 0.05:
            return True, f"Falsified: Error rate increased significantly (+{error_rate_delta * 100:.1f}%)."

        # Check required measurable targets
        for metric_key, target_delta in hypothesis.measurable_outcomes.items():
            if metric_key.startswith("max_"):
                continue
            actual = measured_metrics.get(metric_key)
            if actual is None:
                continue
            # If expected improvement was not met
            if actual < target_delta * 0.5:
                return True, f"Falsified: Measured {metric_key} ({actual:.3f}) failed to achieve required improvement ({target_delta:.3f})."

        return False, "Hypothesis supported by experimental evidence."
