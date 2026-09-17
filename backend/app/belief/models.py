"""SQLAlchemy ORM models for Task 107:
Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class EvidenceSourceModel(Base):
    """Persisted source of evidence."""
    __tablename__ = "belief_evidence_sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    historical_reliability: Mapped[float] = mapped_column(Float, default=0.8)
    provenance_domain: Mapped[str] = mapped_column(String(128), default="system")
    is_verified_authority: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvidenceItemModel(Base):
    """Persisted evidence item."""
    __tablename__ = "belief_evidence_items"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", index=True)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    freshness_ttl_seconds: Mapped[int] = mapped_column(Integer, default=300)
    integrity_verified: Mapped[bool] = mapped_column(Boolean, default=True)
    derived_from_evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    reliability_weight: Mapped[float] = mapped_column(Float, default=0.8)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvidenceRelationshipModel(Base):
    """Persisted relationship between evidence items."""
    __tablename__ = "belief_evidence_relationships"

    relationship_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(64), default="DERIVED_FROM")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class EvidenceAssessmentModel(Base):
    """Persisted arbitration assessment of evidence against a claim."""
    __tablename__ = "belief_evidence_assessments"

    assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(32), default="NEUTRAL", index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    explanation: Mapped[str] = mapped_column(Text, default="")
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ClaimModel(Base):
    """Persisted claim / proposition."""
    __tablename__ = "belief_claims"

    claim_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    object_value_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", index=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.2)
    uncertainty_type: Mapped[str] = mapped_column(String(64), default="NONE")
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ClaimVersionModel(Base):
    """Persisted historical claim version."""
    __tablename__ = "belief_claim_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False)
    object_value_json: Mapped[dict] = mapped_column(JSON, default=dict)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.2)
    uncertainty_type: Mapped[str] = mapped_column(String(64), default="NONE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefModel(Base):
    """Persisted master belief synthesizing claims and evidence."""
    __tablename__ = "belief_manifold"

    belief_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    claim_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", index=True)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty_type: Mapped[str] = mapped_column(String(64), default="NONE")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    freshness_ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    contradiction_evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    provenance_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefVersionModel(Base):
    """Persisted immutable version of a belief."""
    __tablename__ = "belief_manifold_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    belief_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.5)
    uncertainty_type: Mapped[str] = mapped_column(String(64), default="NONE")
    claim_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    contradiction_evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    revision_reason: Mapped[str] = mapped_column(String(64), default="NEW_EVIDENCE")
    revision_notes: Mapped[str] = mapped_column(Text, default="")
    version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefSupportModel(Base):
    """Persisted association link between supporting evidence and a belief."""
    __tablename__ = "belief_manifold_support"

    support_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    belief_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    evidence_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    directness: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefConflictModel(Base):
    """Persisted conflict between claims or beliefs."""
    __tablename__ = "belief_manifold_conflicts"

    conflict_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    belief_id_a: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    belief_id_b: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    claim_id_a: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    claim_id_b: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    conflict_type: Mapped[str] = mapped_column(String(32), default="DIRECT", index=True)
    resolution: Mapped[str] = mapped_column(String(32), default="CONTESTED", index=True)
    competing_evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    rationale: Mapped[str] = mapped_column(Text, default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BeliefRevisionModel(Base):
    """Persisted audit trail record of belief revision."""
    __tablename__ = "belief_manifold_revisions"

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    belief_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prior_version_number: Mapped[int] = mapped_column(Integer, default=1)
    new_version_number: Mapped[int] = mapped_column(Integer, default=2)
    prior_status: Mapped[str] = mapped_column(String(32), default="CANDIDATE")
    new_status: Mapped[str] = mapped_column(String(32), default="SUPPORTED")
    prior_confidence: Mapped[float] = mapped_column(Float, default=0.5)
    new_confidence: Mapped[float] = mapped_column(Float, default=0.6)
    reason: Mapped[str] = mapped_column(String(64), default="NEW_EVIDENCE")
    evidence_id_trigger: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefDependencyModel(Base):
    """Persisted epistemic dependency edge."""
    __tablename__ = "belief_manifold_dependencies"

    dependency_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    parent_belief_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    child_belief_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    dependency_strength: Mapped[float] = mapped_column(Float, default=1.0)
    is_hard_prerequisite: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefSnapshotModel(Base):
    """Persisted immutable point-in-time snapshot."""
    __tablename__ = "belief_manifold_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trigger_type: Mapped[str] = mapped_column(String(64), default="MANUAL", index=True)
    reference_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", index=True)
    beliefs_manifest: Mapped[list] = mapped_column(JSON, default=list)
    evidence_manifest: Mapped[list] = mapped_column(JSON, default=list)
    integrity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefValidationModel(Base):
    """Persisted formal validation event."""
    __tablename__ = "belief_manifold_validations"

    validation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    belief_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    validator_type: Mapped[str] = mapped_column(String(64), default="INDEPENDENT_EVALUATION")
    validator_ref: Mapped[str] = mapped_column(String(128), default="")
    passed: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence_delta: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_produced_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefCorrectionModel(Base):
    """Persisted user or system correction."""
    __tablename__ = "belief_manifold_corrections"

    correction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    belief_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), default="USER")
    correction_statement: Mapped[str] = mapped_column(Text, default="")
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefExpiryModel(Base):
    """Persisted expiry and TTL rule."""
    __tablename__ = "belief_manifold_expiries"

    expiry_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    predicate_pattern: Mapped[str] = mapped_column(String(255), default="*", index=True)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", index=True)
    ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600)
    stale_action: Mapped[str] = mapped_column(String(64), default="REVALIDATION_REQUIRED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class BeliefEventModel(Base):
    """Persisted domain event emitted during belief operations."""
    __tablename__ = "belief_manifold_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    belief_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    emitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
