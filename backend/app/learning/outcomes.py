"""Outcome evaluation models for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class Outcome(BaseModel):
    """Structured evaluation of a task or plan execution (Spec 6)."""

    model_config = ConfigDict(extra="ignore")

    status: str = Field(..., description="SUCCESS, FAILURE, PARTIAL, UNKNOWN")
    success_criteria: list[str] | dict[str, Any] = Field(default_factory=list)
    verification: dict[str, Any] = Field(default_factory=dict)
    evidence: list[str] | dict[str, Any] = Field(default_factory=list)
    duration_ms: float = 0.0
    cost: float = 0.0
    risk: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    user_feedback: dict[str, Any] | None = None
    recovery_required: bool = False

    @property
    def is_verified_success(self) -> bool:
        """True only if status is SUCCESS and verification passed."""
        return self.status.upper() == "SUCCESS" and self.verification.get("status") == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success_criteria": self.success_criteria,
            "verification": self.verification,
            "evidence": self.evidence,
            "duration_ms": round(self.duration_ms, 2),
            "cost": round(self.cost, 4),
            "risk": self.risk,
            "user_feedback": self.user_feedback,
            "recovery_required": self.recovery_required,
            "is_verified_success": self.is_verified_success,
        }


# =============================================================================
# TASK 52 LEARNING OUTCOME EVALUATOR
# =============================================================================

import uuid
from datetime import UTC, datetime


class LearningOutcome(BaseModel):
    """INVARIANT 5: Concrete outcome comparison model for continuous learning."""

    model_config = ConfigDict(extra="ignore")

    outcome_id: str = Field(default_factory=lambda: f"out_{uuid.uuid4().hex[:12]}")
    task_id: str | None = None
    expected: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    deviation: float = 0.0
    deviation_details: dict[str, Any] = Field(default_factory=dict)
    verified: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    learning_trust_weight: float = 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class OutcomeEvaluator:
    """Evaluates task outcomes by comparing expected vs actual states (INVARIANTS 5-10)."""

    @classmethod
    def evaluate_outcome(
        cls,
        expected: dict[str, Any],
        actual: dict[str, Any],
        verification_telemetry: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> LearningOutcome:
        """INVARIANT 6: Compares expected outcome against actual outcome and computes deviations."""
        vt = verification_telemetry or {}
        is_verified = (
            vt.get("verified") is True
            or str(vt.get("status", "")).upper() in ("PASS", "PASSED", "SUCCESS")
            or vt.get("tests_passed") is True
            or str(vt.get("tests", "")).lower() in ("passed", "pass", "ok")
            or bool(vt and not any(v is False or str(v).upper() in ("FAIL", "FAILED", "ERROR") for v in vt.values()))
        )

        deviation_details: dict[str, Any] = {}
        mismatch_count = 0
        total_keys = max(len(expected), 1)

        # Calculate deviations across keys
        for k, v in expected.items():
            actual_val = actual.get(k)
            if actual_val != v:
                deviation_details[k] = {"expected": v, "actual": actual_val}
                mismatch_count += 1

        # Check for unexpected extra outcomes
        for k, v in actual.items():
            if k not in expected:
                deviation_details[f"extra_{k}"] = {"actual": v}
                mismatch_count += 0.5

        deviation_score = round(min(mismatch_count / total_keys, 1.0), 3)

        evidence_refs: list[str] = vt.get("evidence_refs", [])
        if "proof_id" in vt:
            evidence_refs.append(str(vt["proof_id"]))

        trust_weight = 1.0 if is_verified else 0.2

        return LearningOutcome(
            task_id=task_id,
            expected=expected,
            actual=actual,
            deviation=deviation_score,
            deviation_details=deviation_details,
            verified=is_verified,
            evidence_refs=evidence_refs,
            learning_trust_weight=trust_weight,
            timestamp=datetime.now(UTC),
        )

    @classmethod
    def evaluate(
        cls,
        expected: dict[str, Any],
        actual: dict[str, Any],
        verification_telemetry: dict[str, Any] | None = None,
        task_id: str | None = None,
    ) -> LearningOutcome:
        """Convenience alias for evaluate_outcome."""
        return cls.evaluate_outcome(
            expected=expected,
            actual=actual,
            verification_telemetry=verification_telemetry,
            task_id=task_id,
        )

    @classmethod
    def is_unknown(cls, outcome: dict[str, Any] | str) -> bool:
        """INVARIANT 9: Unknown outcome is not failure."""
        if isinstance(outcome, str):
            return outcome.upper() in ("UNKNOWN", "INDETERMINATE")
        status = outcome.get("status", "")
        return str(status).upper() in ("UNKNOWN", "INDETERMINATE")

