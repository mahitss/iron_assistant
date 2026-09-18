"""SQLAlchemy persistence models for Task 115:
Kairo Autonomous Hypothesis Management, Competing Explanations, Evidence Update, Falsification & Uncertainty Resolution Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


class HypothesisSetModel(Base):
    """Authoritative hypothesis set records tracking competing explanations for a target incident."""

    __tablename__ = "hypothesis_sets_t115"

    set_id = Column(String(64), primary_key=True)
    version = Column(Integer, default=1, nullable=False)
    target_description = Column(Text, nullable=False, default="")
    target_incident_id = Column(String(64), nullable=True, index=True)
    scope_json = Column(JSON, nullable=False, default=dict)
    active_hypothesis_ids_json = Column(JSON, nullable=False, default=list)
    rejected_hypothesis_ids_json = Column(JSON, nullable=False, default=list)
    unknown_hypothesis_id = Column(String(64), nullable=True, index=True)
    unresolved_conflicts_json = Column(JSON, nullable=False, default=list)
    relationships_json = Column(JSON, nullable=False, default=list)
    discriminators_json = Column(JSON, nullable=False, default=list)
    information_gaps_json = Column(JSON, nullable=False, default=list)
    is_resolved = Column(Boolean, nullable=False, default=False, index=True)
    resolution_summary = Column(String(128), nullable=False, default="CAUSE_UNKNOWN")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hypotheses = relationship("HypothesisModel", back_populates="hypothesis_set", cascade="all, delete-orphan")
    snapshots = relationship("HypothesisSnapshotModel", back_populates="hypothesis_set", cascade="all, delete-orphan")


class HypothesisModel(Base):
    """First-class representation of an individual competing candidate explanation."""

    __tablename__ = "hypotheses_t115"

    hypothesis_id = Column(String(64), primary_key=True)
    set_id = Column(String(64), ForeignKey("hypothesis_sets_t115.set_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, default=1, nullable=False)
    statement = Column(Text, nullable=False)
    claim_json = Column(JSON, nullable=False, default=dict)
    scope_json = Column(JSON, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="CANDIDATE", index=True)
    provenance = Column(String(32), nullable=False, default="GENERATED")
    proposer_agent_id = Column(String(64), nullable=True, index=True)
    is_unknown_hypothesis = Column(Boolean, nullable=False, default=False, index=True)
    mechanism_summary = Column(Text, nullable=False, default="")
    causal_node_refs_json = Column(JSON, nullable=False, default=list)
    assumptions_json = Column(JSON, nullable=False, default=list)
    falsification_conditions_json = Column(JSON, nullable=False, default=list)
    confidence_profile_json = Column(JSON, nullable=False, default=dict)
    assessments_json = Column(JSON, nullable=False, default=list)
    supporting_evidence_ids_json = Column(JSON, nullable=False, default=list)
    contradicting_evidence_ids_json = Column(JSON, nullable=False, default=list)
    falsifying_evidence_ids_json = Column(JSON, nullable=False, default=list)
    parent_hypothesis_ids_json = Column(JSON, nullable=False, default=list)
    child_hypothesis_ids_json = Column(JSON, nullable=False, default=list)
    superseded_by_id = Column(String(64), nullable=True, index=True)
    stale_at = Column(DateTime(timezone=True), nullable=True)
    staleness_reason = Column(String(256), nullable=True)
    contradiction_search_performed = Column(Boolean, nullable=False, default=False)
    bias_guard_triggers_json = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hypothesis_set = relationship("HypothesisSetModel", back_populates="hypotheses")
    predictions = relationship("HypothesisPredictionModel", back_populates="hypothesis", cascade="all, delete-orphan")


class HypothesisEvidenceModel(Base):
    """Evidence attached to hypotheses with full provenance and independence lineage."""

    __tablename__ = "hypothesis_evidence_t115"

    evidence_id = Column(String(64), primary_key=True)
    source = Column(String(128), nullable=False)
    source_type = Column(String(32), nullable=False, default="system")
    source_agent_id = Column(String(64), nullable=True, index=True)
    independence = Column(String(32), nullable=False, default="INDEPENDENT", index=True)
    evidence_type = Column(String(32), nullable=False, default="OBSERVATION", index=True)
    direct_status = Column(Boolean, nullable=False, default=True)
    freshness_seconds = Column(Float, nullable=False, default=0.0)
    reliability_score = Column(Float, nullable=False, default=1.0)
    is_simulation = Column(Boolean, nullable=False, default=False)
    is_counterfactual = Column(Boolean, nullable=False, default=False)
    provenance = Column(Text, nullable=False, default="")
    parent_evidence_ids_json = Column(JSON, nullable=False, default=list)
    payload_json = Column(JSON, nullable=False, default=dict)
    scope_json = Column(JSON, nullable=True)
    observation_time = Column(DateTime(timezone=True), nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)


class HypothesisPredictionModel(Base):
    """Testable predictions made by hypotheses for calibration and falsification."""

    __tablename__ = "hypothesis_predictions_t115"

    prediction_id = Column(String(64), primary_key=True)
    hypothesis_id = Column(String(64), ForeignKey("hypotheses_t115.hypothesis_id", ondelete="CASCADE"), nullable=False, index=True)
    predicted_event = Column(Text, nullable=False)
    predicted_state_json = Column(JSON, nullable=False, default=dict)
    expected_metric = Column(String(128), nullable=True)
    expected_value_range_json = Column(JSON, nullable=True)
    expected_timing_seconds = Column(Float, nullable=False, default=0.0)
    uncertainty_range = Column(Float, nullable=False, default=0.1)
    source_model = Column(String(64), nullable=False, default="causal_model")
    observed_outcome_json = Column(JSON, nullable=True)
    outcome_status = Column(String(32), nullable=False, default="PENDING", index=True)
    failure_notes = Column(Text, nullable=True)
    validity_window_start = Column(DateTime(timezone=True), nullable=True)
    validity_window_end = Column(DateTime(timezone=True), nullable=True)

    hypothesis = relationship("HypothesisModel", back_populates="predictions")


class HypothesisSnapshotModel(Base):
    """Immutable snapshots of hypothesis sets across time."""

    __tablename__ = "hypothesis_snapshots_t115"

    snapshot_id = Column(String(64), primary_key=True)
    set_id = Column(String(64), ForeignKey("hypothesis_sets_t115.set_id", ondelete="CASCADE"), nullable=False, index=True)
    causal_model_version = Column(String(64), nullable=False, default="causal_v1")
    context_snapshot_id = Column(String(64), nullable=True)
    world_state_id = Column(String(64), nullable=True)
    summary = Column(Text, nullable=False, default="")
    hypotheses_state_json = Column(JSON, nullable=False, default=list)
    evidence_state_json = Column(JSON, nullable=False, default=list)
    relationships_state_json = Column(JSON, nullable=False, default=list)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    hypothesis_set = relationship("HypothesisSetModel", back_populates="snapshots")
