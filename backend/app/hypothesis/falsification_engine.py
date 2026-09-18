"""Autonomous Falsification and Prediction Verification Engine (Task 115 Section 20, 22, 23).

Enforces explicit, bounded, testable falsification conditions on hypotheses and tracks
prediction accuracy over time.

Hard Invariants:
- A hypothesis without falsification conditions is incomplete.
- Falsification is definitive for the current scope/assumptions.
- Prediction failure weakens a hypothesis; it does not automatically purge it if assumptions are uncertain.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.hypothesis.domain import (
    Hypothesis,
    HypothesisStatus,
)

logger = logging.getLogger("kairo.hypothesis.falsification")


class FalsificationEngine:
    """Evaluates whether hypotheses are falsified by observations or failed predictions."""

    def evaluate_falsification_conditions(
        self,
        hyp: Hypothesis,
        observed_signals: Dict[str, Any],
        evidence_id: str,
    ) -> bool:
        """Evaluates whether any falsification condition is met by current observations."""
        if hyp.status in (HypothesisStatus.FALSIFIED, HypothesisStatus.REJECTED):
            return True

        for condition in hyp.falsification_conditions:
            if condition.is_falsified:
                continue

            # Check required observations and metric thresholds
            thresholds_met = 0
            total_thresholds = len(condition.metric_thresholds)

            for metric, bound in condition.metric_thresholds.items():
                if metric in observed_signals:
                    val = float(observed_signals[metric])
                    if val <= float(bound):
                        thresholds_met += 1

            if total_thresholds > 0 and thresholds_met == total_thresholds:
                condition.is_falsified = True
                condition.falsification_evidence_ids.append(evidence_id)
                condition.falsification_reasoning = (
                    f"Falsification triggered: observed signals {observed_signals} satisfied threshold criteria {condition.metric_thresholds}"
                )
                hyp.status = HypothesisStatus.FALSIFIED
                if evidence_id not in hyp.falsifying_evidence_ids:
                    hyp.falsifying_evidence_ids.append(evidence_id)
                hyp.confidence_profile.contradiction_score = 1.0
                hyp.confidence_profile.uncertainty = 0.05
                hyp.updated_at = datetime.now(timezone.utc)
                logger.info(
                    "Hypothesis %s FALSIFIED by condition %s with evidence %s",
                    hyp.hypothesis_id,
                    condition.condition_id,
                    evidence_id,
                )
                return True

        return False

    def evaluate_predictions(
        self,
        hyp: Hypothesis,
        observed_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compares predicted states against real-world observations."""
        results = {"confirmed": 0, "failed": 0, "pending": 0}

        for pred in hyp.predictions:
            if pred.outcome_status in ("CONFIRMED", "FAILED", "EXPIRED"):
                results[pred.outcome_status.lower()] += 1
                continue

            matched = False
            for obs in observed_events:
                if pred.expected_metric and pred.expected_metric in obs:
                    val = float(obs[pred.expected_metric])
                    pred.observed_outcome = val
                    matched = True

                    if pred.expected_value_range:
                        low, high = pred.expected_value_range
                        if low <= val <= high:
                            pred.outcome_status = "CONFIRMED"
                            results["confirmed"] += 1
                        else:
                            pred.outcome_status = "FAILED"
                            pred.failure_notes = f"Observed {val} outside expected range [{low}, {high}]"
                            results["failed"] += 1
                            # Weakens hypothesis
                            hyp.confidence_profile.predictive_success = max(
                                0.0, hyp.confidence_profile.predictive_success - 0.25
                            )
                            hyp.confidence_profile.contradiction_score = min(
                                1.0, hyp.confidence_profile.contradiction_score + 0.2
                            )
                    else:
                        pred.outcome_status = "CONFIRMED"
                        results["confirmed"] += 1
                    break

            if not matched:
                # Check validity window expiration
                now = datetime.now(timezone.utc)
                if pred.validity_window_end and now > pred.validity_window_end:
                    pred.outcome_status = "EXPIRED"
                    results["expired"] = results.get("expired", 0) + 1
                else:
                    results["pending"] += 1

        hyp.updated_at = datetime.now(timezone.utc)
        return results
