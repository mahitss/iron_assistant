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
