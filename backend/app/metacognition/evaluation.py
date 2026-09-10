"""Multi-dimensional metacognitive evaluation without single intelligence score (INVARIANTS 68-71, 181-184)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.metacognition.schemas import MetacognitiveMetricsSchema


class MetacognitiveEvaluator:
    """Tracks dimensional operational performance, avoiding ungrounded single 'intelligence' scores."""

    def __init__(self) -> None:
        self.metrics = MetacognitiveMetricsSchema()
        self._action_samples: int = 0
        self._action_successes: int = 0
        self._verification_attempts: int = 0
        self._verification_successes: int = 0
        self._recovery_attempts: int = 0
        self._recovery_successes: int = 0

    def record_action_outcome(self, was_successful: bool) -> None:
        self._action_samples += 1
        if was_successful:
            self._action_successes += 1
        self.metrics.goal_completion_rate = round(self._action_successes / self._action_samples, 3)

    def record_verification(self, was_verified: bool) -> None:
        self._verification_attempts += 1
        if was_verified:
            self._verification_successes += 1
        self.metrics.verification_rate = round(self._verification_successes / self._verification_attempts, 3)

    def record_recovery(self, was_recovered: bool) -> None:
        self._recovery_attempts += 1
        if was_recovered:
            self._recovery_successes += 1
        self.metrics.error_recovery_rate = round(self._recovery_successes / self._recovery_attempts, 3)

    def record_false_claim(self, claim_type: str) -> None:
        """INVARIANTS 182-184: High-severity evaluation failures for false claims."""
        if claim_type == "CAPABILITY":
            self.metrics.false_capability_claims += 1
            self.metrics.capability_accuracy = max(0.0, self.metrics.capability_accuracy - 0.1)
        elif claim_type == "COMPLETION":
            self.metrics.false_completion_claims += 1
            self.metrics.goal_completion_rate = max(0.0, self.metrics.goal_completion_rate - 0.1)
        elif claim_type == "VERIFICATION":
            self.metrics.false_verification_claims += 1
            self.metrics.verification_rate = max(0.0, self.metrics.verification_rate - 0.1)

    def get_dimensional_report(self) -> Dict[str, Any]:
        """INVARIANT 70, 71, 172: Dimensional reporting strictly preserving separate operational metrics."""
        return {
            "knowledge_accuracy": self.metrics.knowledge_accuracy,
            "confidence_calibration": self.metrics.confidence_calibration,
            "capability_accuracy": self.metrics.capability_accuracy,
            "tool_reliability": self.metrics.tool_reliability,
            "goal_completion_rate": self.metrics.goal_completion_rate,
            "verification_rate": self.metrics.verification_rate,
            "error_recovery_rate": self.metrics.error_recovery_rate,
            "false_capability_claims": self.metrics.false_capability_claims,
            "false_completion_claims": self.metrics.false_completion_claims,
            "false_verification_claims": self.metrics.false_verification_claims,
            "penalties": {
                "false_capability_claims": self.metrics.false_capability_claims,
                "false_completion_claims": self.metrics.false_completion_claims,
                "false_verification_claims": self.metrics.false_verification_claims,
            },
        }
