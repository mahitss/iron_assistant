"""Claim domain models, ClaimTypes, and TruthStatuses for Kairo Truth Engine (Task 42)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class ClaimType(str, Enum):
    """Authoritative classifications of claims (Spec 3)."""

    FACT = "FACT"
    STATE = "STATE"
    PREDICTION = "PREDICTION"
    PLAN_EXPECTATION = "PLAN_EXPECTATION"
    MODEL_ASSERTION = "MODEL_ASSERTION"
    TOOL_REPORT = "TOOL_REPORT"
    USER_ASSERTION = "USER_ASSERTION"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"


class TruthStatus(str, Enum):
    """Authoritative truth validation states of a claim (Spec 4-12)."""

    VERIFIED = "VERIFIED"          # Independent verification criteria succeeded
    SUPPORTED = "SUPPORTED"        # Corroborated by evidence but not yet independently verified
    UNVERIFIED = "UNVERIFIED"      # Claim exists but sufficient evidence is absent
    CONTRADICTED = "CONTRADICTED"  # Reliable evidence conflicts with the claim
    UNKNOWN = "UNKNOWN"            # Evidence is insufficient to determine truth
    STALE = "STALE"                # Previously supported claim has expired
    INVALID = "INVALID"            # Claim violates schema or domain invariants
    REJECTED = "REJECTED"          # Claim cannot be accepted as trustworthy


class ClaimScope(BaseModel):
    """Scope boundary for a claim."""

    model_config = ConfigDict(extra="ignore")

    user_id: str = "default_user"
    project_id: str | None = None
    resource: str | None = None


class Claim(BaseModel):
    """An asserted statement about reality or system state (Spec 2)."""

    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:12]}")
    statement: str = Field(..., min_length=1, description="Exact factual statement")
    subject: str | None = Field(default=None, description="Subject of the claim (e.g. 'api_service')")
    predicate: str | None = Field(default=None, description="Predicate relation (e.g. 'is_healthy', 'status')")
    object_ref: str | None = Field(default=None, description="Value or object reference (e.g. 'true', 'v1.2.0')")
    source: str = Field(default="system", description="Origin (e.g. 'model', 'tool', 'system', 'user')")
    claim_type: ClaimType = Field(default=ClaimType.FACT)
    truth_status: TruthStatus = Field(default=TruthStatus.UNVERIFIED)
    confidence: str = Field(default="LOW", description="LOW, MEDIUM, HIGH")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list, description="IDs of corroborating Evidence records")
    scope: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    observed_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = Field(default=None)

    def mark_verified(self, evidence_id: str, confidence_score: float = 0.95) -> None:
        """Mark claim as verified by empirical evidence."""
        self.truth_status = TruthStatus.VERIFIED
        self.confidence = "HIGH"
        self.confidence_score = confidence_score
        if evidence_id not in self.evidence_refs:
            self.evidence_refs.append(evidence_id)

    def mark_contradicted(self, evidence_id: str) -> None:
        """Mark claim as contradicted by conflicting evidence."""
        self.truth_status = TruthStatus.CONTRADICTED
        self.confidence = "LOW"
        self.confidence_score = 0.1
        if evidence_id not in self.evidence_refs:
            self.evidence_refs.append(evidence_id)

    def mark_stale(self) -> None:
        """Mark claim as expired/stale."""
        self.truth_status = TruthStatus.STALE
        self.confidence_score = max(0.1, self.confidence_score * 0.5)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "subject": self.subject,
            "predicate": self.predicate,
            "object_ref": self.object_ref,
            "source": self.source,
            "claim_type": self.claim_type.value if hasattr(self.claim_type, "value") else str(self.claim_type),
            "truth_status": self.truth_status.value if hasattr(self.truth_status, "value") else str(self.truth_status),
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "evidence_refs": self.evidence_refs,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "observed_at": self.observed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
