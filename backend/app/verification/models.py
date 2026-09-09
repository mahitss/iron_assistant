"""SQLAlchemy ORM models for Kairo Truth, Verification, and Self-Correction (Task 42)."""

from datetime import UTC, datetime
from typing import Any
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class VerificationClaimModel(Base):
    """Authoritative persistent record of a factual claim or state assertion."""

    __tablename__ = "verification_claims"

    claim_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(128), nullable=False)
    predicate: Mapped[str] = mapped_column(String(128), nullable=False)
    object_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False, default="FACT", index=True)
    truth_status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIED", index=True)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class VerificationEvidenceModel(Base):
    """Empirical observation supporting or refuting claims."""

    __tablename__ = "verification_evidence"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    observation: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    reliability: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    freshness_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=300.0)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class VerificationContractModel(Base):
    """Specification of required tests, queries, or checks to establish truth."""

    __tablename__ = "verification_contracts"

    contract_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target: Mapped[str] = mapped_column(String(256), nullable=False)
    expected_state: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    verification_steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    timeout_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=30.0)
    required_evidence: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    failure_behavior: Mapped[str] = mapped_column(String(32), nullable=False, default="BLOCK")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class VerificationResultModel(Base):
    """Outcome of running a verification contract."""

    __tablename__ = "verification_results"

    result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    contract_id: Mapped[str] = mapped_column(String(64), ForeignKey("verification_contracts.contract_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("verification_claims.claim_id", ondelete="CASCADE"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN", index=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    discrepancies: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="MEDIUM")
    verifier: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class VerificationCorrectionModel(Base):
    """Audit log of identified falsehoods and empirical corrections."""

    __tablename__ = "verification_corrections"

    correction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_claim_id: Mapped[str] = mapped_column(String(64), ForeignKey("verification_claims.claim_id", ondelete="CASCADE"), nullable=False)
    corrected_claim_id: Mapped[str] = mapped_column(String(64), ForeignKey("verification_claims.claim_id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class VerificationInvariantModel(Base):
    """Universal state and security invariants verified continuously."""

    __tablename__ = "verification_invariants"

    invariant_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="HIGH")
    predicate_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
