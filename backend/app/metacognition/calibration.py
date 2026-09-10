"""Confidence calibration against verified outcomes; detects overconfidence and underconfidence (INVARIANTS 27-30)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ConfidenceCalibrator:
    """Evaluates prediction/assertion confidence against verified ground truth."""

    def __init__(self) -> None:
        # list of records: (claimed_confidence, outcome_success: bool)
        self._history: List[Dict[str, Any]] = []
        self.overconfidence_events: int = 0
        self.underconfidence_events: int = 0

    def record_outcome(self, claimed_confidence: float, was_successful: bool, task_id: Optional[str] = None) -> Dict[str, Any]:
        """INVARIANT 27: Compares claimed confidence against actual verified outcome."""
        rec = {
            "claimed_confidence": claimed_confidence,
            "was_successful": was_successful,
            "task_id": task_id,
        }
        self._history.append(rec)

        # INVARIANT 28: Overconfidence = High confidence (>= 0.85) but failed
        if claimed_confidence >= 0.85 and not was_successful:
            self.overconfidence_events += 1

        # INVARIANT 29: Underconfidence = Low confidence (<= 0.50) but repeatedly succeeded
        if claimed_confidence <= 0.50 and was_successful:
            self.underconfidence_events += 1

        return rec

    def compute_calibration_factor(self) -> float:
        """Calculates adjustment factor. If overconfident, factor drops below 1.0; if underconfident, rises above 1.0."""
        if len(self._history) < 5:
            return 1.0

        high_conf_samples = [h for h in self._history if h["claimed_confidence"] >= 0.8]
        if not high_conf_samples:
            return 1.0

        actual_success_rate = sum(1 for h in high_conf_samples if h["was_successful"]) / len(high_conf_samples)
        expected_rate = 0.85

        # If actual success is lower than expected, damp future confidence
        factor = actual_success_rate / expected_rate
        return min(max(factor, 0.6), 1.3)

    def get_metrics(self) -> Dict[str, Any]:
        total = len(self._history)
        successes = sum(1 for h in self._history if h["was_successful"])
        return {
            "total_samples": total,
            "overall_accuracy": round(successes / total, 3) if total > 0 else 1.0,
            "overconfidence_events": self.overconfidence_events,
            "underconfidence_events": self.underconfidence_events,
            "suggested_calibration_factor": round(self.compute_calibration_factor(), 3),
        }
