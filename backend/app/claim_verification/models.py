"""SQLAlchemy persistence models for Task 116:
Kairo Autonomous Claim Verification, Source Integrity & Evidence Provenance Engine.
Tables use _t116 suffix to avoid collisions and maintain strict isolation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


class VerificationCaseModel(Base):
    """Authoritative claim verification case lifecycle and tracking entity."""

    __tablename__ = "verification_cases_t116"

    case_id = Column(String(64), primary_key=True)
    version = Column(Integer, default=1, nullable=False)
    title = Column(String(256), nullable=False)
    claim_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="REQUESTED", index=True)
    scope_json = Column(JSON, nullable=False, default=dict)
    assumptions_json = Column(JSON, nullable=False, default=list)
    falsification_conditions_json = Column(JSON, nullable=False, default=list)
    verification_requirements_json = Column(JSON, nullable=False, default=list)
    resolution_summary = Column(Text, nullable=False, default="")
    idempotency_key = Column(String(128), nullable=True, unique=True, index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    superseded_by_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    results = relationship("VerificationResultModel", back_populates="case", cascade="all, delete-orphan")
    snapshots = relationship("VerificationSnapshotModel", back_populates="case", cascade="all, delete-orphan")
    events = relationship("VerificationEventModel", back_populates="case", cascade="all, delete-orphan")
    gaps = relationship("VerificationGapModel", back_populates="case", cascade="all, delete-orphan")
    corroborations = relationship("CorroborationGroupModel", back_populates="case", cascade="all, delete-orphan")
    contradictions = relationship("ContradictionRecordModel", back_populates="case", cascade="all, delete-orphan")
    reproductions = relationship("ReproductionAttemptModel", back_populates="case", cascade="all, delete-orphan")


class ClaimModel(Base):
    """Structured claim representation."""

    __tablename__ = "claims_t116"

    claim_id = Column(String(64), primary_key=True)
    version = Column(Integer, default=1, nullable=False)
    canonical_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    claim_type = Column(String(32), nullable=False, default="ATOMIC", index=True)
    subject = Column(String(128), nullable=False, default="")
    predicate = Column(String(128), nullable=False, default="")
    object_val = Column(Text, nullable=False, default="")
    qualifiers_json = Column(JSON, nullable=False, default=dict)
    temporal_scope_json = Column(JSON, nullable=False, default=dict)
    spatial_scope_json = Column(JSON, nullable=False, default=dict)
    entity_scope_json = Column(JSON, nullable=False, default=list)
    source_scope_json = Column(JSON, nullable=False, default=dict)
    falsification_conditions_json = Column(JSON, nullable=False, default=list)
    expected_evidence_types_json = Column(JSON, nullable=False, default=list)
    confidence = Column(Float, nullable=False, default=0.5)
    uncertainty = Column(Float, nullable=False, default=0.5)
    provenance_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    fragments = relationship("ClaimFragmentModel", back_populates="claim", cascade="all, delete-orphan")


class ClaimFragmentModel(Base):
    """Decomposed atomic/causal/temporal fragment of a composite claim."""

    __tablename__ = "claim_fragments_t116"

    fragment_id = Column(String(64), primary_key=True)
    claim_id = Column(String(64), ForeignKey("claims_t116.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    fragment_type = Column(String(32), nullable=False, default="ATOMIC")
    statement = Column(Text, nullable=False)
    subject = Column(String(128), nullable=False, default="")
    predicate = Column(String(128), nullable=False, default="")
    object_val = Column(Text, nullable=False, default="")
    dependencies_json = Column(JSON, nullable=False, default=list)
    order_idx = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    claim = relationship("ClaimModel", back_populates="fragments")


class SourceModel(Base):
    """Explicit source identity and trust profile."""

    __tablename__ = "sources_t116"

    source_id = Column(String(64), primary_key=True)
    uri = Column(String(512), nullable=False, index=True)
    category = Column(String(32), nullable=False, default="UNKNOWN", index=True)
    publisher = Column(String(256), nullable=False, default="")
    owner = Column(String(256), nullable=False, default="")
    auth_state = Column(String(32), nullable=False, default="UNAUTHENTICATED")
    trust_profile_json = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    snapshots = relationship("SourceSnapshotModel", back_populates="source", cascade="all, delete-orphan")
    evidence_artifacts = relationship("EvidenceArtifactModel", back_populates="source", cascade="all, delete-orphan")


class SourceSnapshotModel(Base):
    """Immutable point-in-time snapshot of mutable sources."""

    __tablename__ = "source_snapshots_t116"

    snapshot_id = Column(String(64), primary_key=True)
    source_id = Column(String(64), ForeignKey("sources_t116.source_id", ondelete="CASCADE"), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    headers_json = Column(JSON, nullable=False, default=dict)
    content_metadata_json = Column(JSON, nullable=False, default=dict)
    content_preview = Column(Text, nullable=False, default="")
    parser_version = Column(String(64), nullable=False, default="default_v1")
    retrieved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    valid_at = Column(DateTime(timezone=True), nullable=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)

    source = relationship("SourceModel", back_populates="snapshots")


class SourceRelationshipModel(Base):
    """Relationship and dependency between sources (copying, citation, etc.)."""

    __tablename__ = "source_relationships_t116"

    relationship_id = Column(String(64), primary_key=True)
    source_a_id = Column(String(64), nullable=False, index=True)
    source_b_id = Column(String(64), nullable=False, index=True)
    relationship_type = Column(String(32), nullable=False, default="INDEPENDENT", index=True)
    confidence = Column(Float, nullable=False, default=0.5)
    justification = Column(Text, nullable=False, default="")
    observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class EvidenceArtifactModel(Base):
    """Extracted evidence with precise lineage and quality dimensions."""

    __tablename__ = "evidence_artifacts_t116"

    evidence_id = Column(String(64), primary_key=True)
    source_id = Column(String(64), ForeignKey("sources_t116.source_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_id = Column(String(64), nullable=True, index=True)
    location = Column(String(512), nullable=False, default="")
    offset_range = Column(String(128), nullable=False, default="")
    content_hash = Column(String(64), nullable=False, index=True)
    content_text = Column(Text, nullable=False, default="")
    quality_profile_json = Column(JSON, nullable=False, default=dict)
    direct_status = Column(Boolean, nullable=False, default=True)
    is_synthetic = Column(Boolean, nullable=False, default=False)
    is_simulated = Column(Boolean, nullable=False, default=False)
    is_counterfactual = Column(Boolean, nullable=False, default=False)
    parent_artifact_id = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    source = relationship("SourceModel", back_populates="evidence_artifacts")


class EvidenceTransformationModel(Base):
    """Audit record for transformation operations applied to evidence."""

    __tablename__ = "evidence_transformations_t116"

    transformation_id = Column(String(64), primary_key=True)
    input_artifact_ids_json = Column(JSON, nullable=False, default=list)
    output_artifact_id = Column(String(64), nullable=False, index=True)
    operation = Column(String(64), nullable=False)
    component = Column(String(128), nullable=False)
    config_fingerprint = Column(String(64), nullable=False, default="")
    is_deterministic = Column(Boolean, nullable=False, default=True)
    input_hash = Column(String(64), nullable=False, default="")
    output_hash = Column(String(64), nullable=False, default="")
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class ProvenanceLinkModel(Base):
    """W3C-PROV inspired directed provenance link."""

    __tablename__ = "provenance_links_t116"

    link_id = Column(String(64), primary_key=True)
    from_entity_type = Column(String(32), nullable=False, index=True)
    from_entity_id = Column(String(64), nullable=False, index=True)
    to_entity_type = Column(String(32), nullable=False, index=True)
    to_entity_id = Column(String(64), nullable=False, index=True)
    predicate = Column(String(32), nullable=False, default="DERIVED_FROM", index=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class CorroborationGroupModel(Base):
    """Group of evidence corroborating a claim."""

    __tablename__ = "corroboration_groups_t116"

    group_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id = Column(String(64), nullable=False, index=True)
    corroboration_type = Column(String(32), nullable=False, default="INDEPENDENT_SUPPORT", index=True)
    evidence_ids_json = Column(JSON, nullable=False, default=list)
    source_ids_json = Column(JSON, nullable=False, default=list)
    temporal_alignment = Column(Float, nullable=False, default=1.0)
    semantic_alignment = Column(Float, nullable=False, default=1.0)
    scope_alignment = Column(Float, nullable=False, default=1.0)
    independence_assessment_json = Column(JSON, nullable=False, default=dict)
    summary = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    case = relationship("VerificationCaseModel", back_populates="corroborations")


class ContradictionRecordModel(Base):
    """Contradiction record between claims or evidence."""

    __tablename__ = "contradiction_records_t116"

    contradiction_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True)
    contradiction_type = Column(String(32), nullable=False, default="DIRECT_CONTRADICTION", index=True)
    claim_a_id = Column(String(64), nullable=False, index=True)
    claim_b_id = Column(String(64), nullable=True, index=True)
    evidence_a_id = Column(String(64), nullable=False, index=True)
    evidence_b_id = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=False)
    severity = Column(Float, nullable=False, default=1.0)
    status = Column(String(32), nullable=False, default="OPEN", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    case = relationship("VerificationCaseModel", back_populates="contradictions")


class ReproductionAttemptModel(Base):
    """Audit record for reproduction attempts."""

    __tablename__ = "reproduction_attempts_t116"

    attempt_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True)
    method = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="NOT_ATTEMPTED", index=True)
    environment_fingerprint = Column(String(64), nullable=False, default="")
    input_hash = Column(String(64), nullable=False, default="")
    output_hash = Column(String(64), nullable=False, default="")
    deterministic = Column(Boolean, nullable=False, default=True)
    seed = Column(Integer, nullable=True)
    notes = Column(Text, nullable=False, default="")
    executed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    case = relationship("VerificationCaseModel", back_populates="reproductions")


class VerificationResultModel(Base):
    """Final structured verification result."""

    __tablename__ = "verification_results_t116"

    result_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id = Column(String(64), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="UNKNOWN", index=True)
    scope_json = Column(JSON, nullable=False, default=dict)
    justification = Column(Text, nullable=False, default="")
    evidence_ids_json = Column(JSON, nullable=False, default=list)
    contradiction_ids_json = Column(JSON, nullable=False, default=list)
    method_types_json = Column(JSON, nullable=False, default=list)
    uncertainty_profile_json = Column(JSON, nullable=False, default=dict)
    gaps_json = Column(JSON, nullable=False, default=list)
    reproducibility_status = Column(String(32), nullable=False, default="NOT_ATTEMPTED")
    validity_window_start = Column(DateTime(timezone=True), nullable=True)
    validity_window_end = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    case = relationship("VerificationCaseModel", back_populates="results")


class VerificationGapModel(Base):
    """Unresolved verification gap requiring active observation or more evidence."""

    __tablename__ = "verification_gaps_t116"

    gap_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True)
    missing_evidence_desc = Column(Text, nullable=False)
    impact_reason = Column(Text, nullable=False)
    affected_claim_id = Column(String(64), nullable=False, index=True)
    possible_methods_json = Column(JSON, nullable=False, default=list)
    expected_info_gain = Column(Float, nullable=False, default=0.5)
    cost = Column(Float, nullable=False, default=0.1)
    risk = Column(Float, nullable=False, default=0.1)
    urgency = Column(Float, nullable=False, default=0.5)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    case = relationship("VerificationCaseModel", back_populates="gaps")


class VerificationSnapshotModel(Base):
    """Immutable state snapshot for point-in-time auditability."""

    __tablename__ = "verification_snapshots_t116"

    snapshot_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_version = Column(Integer, nullable=False, default=1)
    case_state_json = Column(JSON, nullable=False, default=dict)
    summary = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    case = relationship("VerificationCaseModel", back_populates="snapshots")


class VerificationEventModel(Base):
    """Append-only verification lifecycle event record."""

    __tablename__ = "verification_events_t116"

    event_id = Column(String(64), primary_key=True)
    case_id = Column(String(64), ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(64), nullable=False, default="system")
    correlation_id = Column(String(64), nullable=True, index=True)
    causation_id = Column(String(64), nullable=True)
    payload_json = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    case = relationship("VerificationCaseModel", back_populates="events")
