"""Feedback ingestion, trust hierarchy scoring, and poisoning defense (Task 62)."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from app.optimization.safety import (
    sanitize_optimization_directive,
)
from app.optimization.schemas import FeedbackSignal, FeedbackTrustLevel

logger = logging.getLogger(__name__)

# Canonical trust hierarchy weights
_TRUST_WEIGHTS = {
    FeedbackTrustLevel.VERIFIED_SYSTEM: 1.0,
    FeedbackTrustLevel.VERIFIED_EXTERNAL: 0.85,
    FeedbackTrustLevel.TRUSTED_HUMAN: 0.80,
    FeedbackTrustLevel.OPERATIONAL_OBSERVATION: 0.65,
    FeedbackTrustLevel.MODEL_JUDGMENT: 0.45,
    FeedbackTrustLevel.UNVERIFIED_EXTERNAL: 0.20,
}


class FeedbackEngine:
    """Ingests operational feedback, enforces strict trust weighting, and neutralizes poisoning attempts.

    Invariant 11 & 12: Feedback is data, not authority. External feedback text can never become
    unrestricted system instruction or bypass safety boundaries.
    """

    def __init__(self, max_signals_per_key: int = 200) -> None:
        self._signals: dict[str, list[FeedbackSignal]] = defaultdict(list)
        self._max_signals = max_signals_per_key

    def record_feedback(
        self,
        source: str,
        content: str,
        trust_level: FeedbackTrustLevel = FeedbackTrustLevel.OPERATIONAL_OBSERVATION,
        numeric_feedback: float | None = None,
        metric_name: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> FeedbackSignal:
        """Record and sanitize feedback with provenance.

        Raises:
            OptimizationSafetyError: If prompt injection or malicious directive is detected.
        """
        # Invariant 12: Neutralize adversarial instructions and prompt injection
        clean_content = sanitize_optimization_directive(content)

        signal = FeedbackSignal(
            source=source,
            trust_level=trust_level,
            content=clean_content,
            numeric_feedback=numeric_feedback,
            metric_name=metric_name,
            provenance=provenance or {"raw_source": source},
        )

        key = metric_name or "general"
        history = self._signals[key]
        history.append(signal)
        if len(history) > self._max_signals:
            self._signals[key] = history[-self._max_signals :]

        logger.info(
            "FEEDBACK_RECORDED: key=%s trust=%s source=%s",
            key,
            trust_level.value,
            source,
        )
        return signal

    def get_weighted_feedback_score(self, metric_name: str) -> float | None:
        """Compute trust-weighted average of numeric feedback for a metric."""
        signals = self._signals.get(metric_name, [])
        numeric_signals = [s for s in signals if s.numeric_feedback is not None]
        if not numeric_signals:
            return None

        total_weight = 0.0
        weighted_sum = 0.0
        for s in numeric_signals:
            weight = _TRUST_WEIGHTS.get(s.trust_level, 0.20)
            total_weight += weight
            weighted_sum += (s.numeric_feedback or 0.0) * weight

        if total_weight <= 0:
            return None
        return round(weighted_sum / total_weight, 4)

    def list_feedback(self, metric_name: str | None = None) -> list[FeedbackSignal]:
        """Retrieve recorded feedback signals."""
        if metric_name:
            return list(self._signals.get(metric_name, []))
        all_signals: list[FeedbackSignal] = []
        for sig_list in self._signals.values():
            all_signals.extend(sig_list)
        return all_signals


feedback_engine = FeedbackEngine()
