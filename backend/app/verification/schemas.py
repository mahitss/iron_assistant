"""Pydantic schemas for Kairo Truth, Verification & Self-Correction Engine (Task 42)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.verification.assertions import VerificationStatus
from app.verification.claims import ClaimType, TruthStatus
from app.verification.confidence import ConfidenceLevel, UncertaintyState
from app.verification.evidence import EvidenceType
from app.verification.strategies import VerificationStrategyType


class ClaimCreateRequest(BaseModel):
    statement: str = Field(..., min_length=1, description="Textual claim statement")
    claim_type: ClaimType = Field(default=ClaimType.MODEL_ASSERTION)
    subject: str | None = Field(default=None, description="Entity or resource subject")
    predicate: str | None = Field(default=None, description="Relation or property")
    object_ref: str | None = Field(default=None, description="Target value or state")
    source: str = Field(default="model", description="Origin of claim")
    scope: dict[str, Any] = Field(default_factory=dict, description="User, project, or domain scope")
    expires_at: datetime | None = Field(default=None, description="Optional TTL expiration")


class ClaimResponse(BaseModel):
    claim_id: str
    statement: str
    claim_type: str
    subject: str | None = None
    predicate: str | None = None
    object_ref: str | None = None
    source: str
    scope: dict[str, Any]
    truth_status: str
    confidence: str
    evidence_refs: list[str]
    created_at: str
    observed_at: str
    expires_at: str | None = None


class EvidenceCreateRequest(BaseModel):
    source_type: EvidenceType = Field(...)
    source_reference: str = Field(...)
    observation: dict[str, Any] | str = Field(...)
    claim_id: str | None = Field(default=None)
    scope: dict[str, Any] = Field(default_factory=dict)
    checksum: str | None = Field(default=None)


class EvidenceResponse(BaseModel):
    evidence_id: str
    source_type: str
    source_reference: str
    observation: dict[str, Any]
    observed_at: str
    reliability: float
    freshness_score: float
    scope: dict[str, Any]
    checksum: str | None = None


class VerificationContractRequest(BaseModel):
    target: str = Field(...)
    expected_state: dict[str, Any] = Field(...)
    verification_steps: list[str] = Field(default_factory=list)
    timeout_seconds: float = Field(default=30.0)
    strategy: VerificationStrategyType = Field(default=VerificationStrategyType.DIRECT_CHECK)
    observed_data: dict[str, Any] = Field(default_factory=dict)


class VerificationResultResponse(BaseModel):
    status: str
    discrepancies: list[str]
    confidence: str
    verifier: str
    evidence_ids: list[str]
    duration_ms: float
    checked_at: str


class TriangulateResponse(BaseModel):
    claim_id: str
    num_sources: int
    num_independent_sources: int
    agreement_ratio: float
    is_corroborated: bool
    status: str
    discrepancies: list[str]
    participating_evidence_ids: list[str]
    metadata: dict[str, Any]


class ConfidenceResponse(BaseModel):
    level: str
    uncertainty_state: str
    score: float
    factors: dict[str, float]
    explanation: str
    calibrated_at: str


class SelfCorrectionRequest(BaseModel):
    original_claim_id: str = Field(...)
    corrected_statement: str = Field(...)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    reason: str = Field(...)


class CorrectionResponse(BaseModel):
    correction_id: str
    original_claim_id: str
    original_statement: str
    corrected_statement: str
    evidence_ids: list[str]
    reason: str
    user_admission: str
    timestamp: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CitationValidateRequest(BaseModel):
    statement: str = Field(...)
    citation_ref: str = Field(...)
    excerpt: str | None = Field(default=None)


class CitationValidationResponse(BaseModel):
    citation_ref: str
    is_valid: bool
    exists: bool
    supports_claim: bool
    rejection_reason: str | None = None
    extracted_quote: str | None = None
    evaluated_at: str


class InvariantViolationResponse(BaseModel):
    rule_id: str
    severity: str
    message: str
    details: dict[str, Any]


class VerificationStatsResponse(BaseModel):
    metrics: dict[str, int]
    total_claims: int
    total_evidence: int
    total_contracts: int
    total_corrections: int
    calibration: dict[str, Any]
