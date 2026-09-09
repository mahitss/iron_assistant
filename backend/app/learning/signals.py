"""Learning signals, signal types, and source priorities for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class SignalType(str, enum.Enum):
    """Classifications of feedback or performance learning signals (Spec 8)."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    CORRECTION = "CORRECTION"
    REGRESSION = "REGRESSION"
    IMPROVEMENT = "IMPROVEMENT"
    DEGRADATION = "DEGRADATION"


class SignalSource(str, enum.Enum):
    """Recognized origins of learning signals (Spec 9)."""

    VERIFICATION = "verification"
    TESTS = "tests"
    TOOL_OUTCOMES = "tool_outcomes"
    USER_FEEDBACK = "user_feedback"
    SYSTEM_METRICS = "system_metrics"
    INCIDENT_OUTCOMES = "incident_outcomes"
    TASK_COMPLETION = "task_completion"
    RECOVERY_RESULTS = "recovery_results"
    EVALUATION_BENCHMARKS = "evaluation_benchmarks"


# Source priority weights (Spec 10: Verified objective outcomes outrank subjective signals)
SOURCE_PRIORITY_WEIGHTS: dict[str, float] = {
    SignalSource.VERIFICATION.value: 1.0,
    SignalSource.TESTS.value: 0.95,
    SignalSource.INCIDENT_OUTCOMES.value: 0.95,
    SignalSource.EVALUATION_BENCHMARKS.value: 0.90,
    SignalSource.TOOL_OUTCOMES.value: 0.85,
    SignalSource.RECOVERY_RESULTS.value: 0.85,
    SignalSource.TASK_COMPLETION.value: 0.80,
    SignalSource.SYSTEM_METRICS.value: 0.75,
    SignalSource.USER_FEEDBACK.value: 0.65,  # Subjective signals valuable for UX, but cannot override objective proof
}


class LearningSignal(BaseModel):
    """A quantified performance or feedback signal (Spec 7)."""

    model_config = ConfigDict(extra="ignore")

    signal_id: str = Field(default_factory=lambda: f"sig_{uuid.uuid4().hex[:12]}")
    source: SignalSource = Field(default=SignalSource.VERIFICATION)
    signal_type: SignalType = Field(default=SignalType.NEUTRAL)
    strength: float = Field(default=1.0, ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(default_factory=dict)
    confidence: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    scope: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    def effective_weight(self) -> float:
        """Compute final signal impact factoring in source authority."""
        source_key = self.source.value if hasattr(self.source, "value") else str(self.source)
        source_factor = SOURCE_PRIORITY_WEIGHTS.get(source_key, 0.5)
        conf_factor = 1.0 if self.confidence == "HIGH" else (0.75 if self.confidence == "MEDIUM" else 0.4)
        return round(self.strength * source_factor * conf_factor, 3)

    @classmethod
    def create_false_success_signal(cls, strategy: str, claimed_status: str, verification_result: dict[str, Any]) -> "LearningSignal":
        """Generate strong negative signal for false successes (Spec 29)."""
        return cls(
            source=SignalSource.VERIFICATION,
            signal_type=SignalType.REGRESSION,
            strength=1.0,
            confidence="HIGH",
            evidence={
                "strategy": strategy,
                "claimed_status": claimed_status,
                "verification_result": verification_result,
                "reason": "Claimed success contradicted by empirical verification failure.",
            },
        )

    @classmethod
    def create_false_failure_signal(cls, strategy: str, verification_result: dict[str, Any]) -> "LearningSignal":
        """Record correction signal when verification proves success despite reported failure (Spec 30)."""
        return cls(
            source=SignalSource.VERIFICATION,
            signal_type=SignalType.CORRECTION,
            strength=0.85,
            confidence="HIGH",
            evidence={
                "strategy": strategy,
                "verification_result": verification_result,
                "reason": "Execution reported failure but empirical verification established success.",
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "source": self.source.value if hasattr(self.source, "value") else str(self.source),
            "signal_type": self.signal_type.value if hasattr(self.signal_type, "value") else str(self.signal_type),
            "strength": round(self.strength, 3),
            "effective_weight": self.effective_weight(),
            "evidence": self.evidence,
            "confidence": self.confidence,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
        }
