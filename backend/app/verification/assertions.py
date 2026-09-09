"""VerificationContract and VerificationResult models for Kairo Truth Engine (Task 42).

Enforces:
1. Verification must default to strictly read-only; never produce unintended side effects (Spec 58, 59).
2. Verification timeouts must NEVER be treated as success (Spec 54).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class VerificationStatus(str, Enum):
    """Authoritative outcome status of a verification check (Spec 53)."""

    PASS = "PASS"
    FAIL = "FAIL"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    TIMEOUT = "TIMEOUT"
    INCONCLUSIVE = "INCONCLUSIVE"


class VerificationContract(BaseModel):
    """Contract defining required checks, target, and expected outcome (Spec 49)."""

    model_config = ConfigDict(extra="ignore")

    contract_id: str = Field(default_factory=lambda: f"vct_{uuid.uuid4().hex[:10]}")
    target: str = Field(..., description="Target system, endpoint, artifact, or entity")
    expected_state: dict[str, Any] = Field(default_factory=dict, description="Expected keys and values")
    verification_steps: list[Any] = Field(default_factory=list, description="Ordered verification checks")
    timeout_seconds: float = Field(default=30.0, description="Strict timeout limit")
    required_evidence: list[str] = Field(default_factory=list, description="Required evidence types")
    failure_behavior: str = Field(default="BLOCK", description="BLOCK, REPLAN, RETRY, ESCALATE")

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "target": self.target,
            "expected_state": self.expected_state,
            "verification_steps": self.verification_steps,
            "timeout_seconds": self.timeout_seconds,
            "required_evidence": self.required_evidence,
            "failure_behavior": self.failure_behavior,
        }


class VerificationResult(BaseModel):
    """Immutable result of executing a verification contract (Spec 52)."""

    model_config = ConfigDict(extra="ignore")

    result_id: str = Field(default_factory=lambda: f"vrs_{uuid.uuid4().hex[:10]}")
    contract_id: str = Field(default_factory=lambda: f"vct_{uuid.uuid4().hex[:10]}")
    claim_id: str | None = None
    status: VerificationStatus = Field(default=VerificationStatus.UNKNOWN)
    evidence: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    discrepancies: list[str] = Field(default_factory=list)
    confidence: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH")
    verifier: str = Field(default="system")
    duration_ms: float = Field(default=0.0)
    checked_at: datetime = Field(default_factory=utc_now)

    @property
    def is_successful(self) -> bool:
        """Only PASS is considered successful. TIMEOUT, FAIL, UNKNOWN, INCONCLUSIVE are not."""
        return self.status == VerificationStatus.PASS

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "contract_id": self.contract_id,
            "claim_id": self.claim_id,
            "status": self.status.value,
            "evidence": self.evidence,
            "evidence_ids": self.evidence_ids,
            "discrepancies": self.discrepancies,
            "confidence": self.confidence,
            "verifier": self.verifier,
            "duration_ms": round(self.duration_ms, 2),
            "checked_at": self.checked_at.isoformat(),
        }
