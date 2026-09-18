"""SQLAlchemy persistence models for Task 114:
Autonomous Active Observation, Value-of-Information, Information Acquisition & Uncertainty Reduction Engine.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ObservationPlanModel(Base):
    """Authoritative observation plan records (Section 4, 14, 49)."""

    __tablename__ = "observation_plans_t114"

    plan_id = Column(String(64), primary_key=True)
    version = Column(Integer, default=1, nullable=False)
    objective = Column(Text, nullable=False, default="")
    target_entity = Column(String(128), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="IDENTIFIED", index=True)
    recommended_stance = Column(String(32), nullable=False, default="OBSERVE")
    budget_allocated = Column(Float, nullable=False, default=10.0)
    budget_spent = Column(Float, nullable=False, default=0.0)
    stop_reason = Column(String(64), nullable=True)
    is_stale = Column(Boolean, nullable=False, default=False, index=True)
    stale_reason = Column(String(256), nullable=False, default="")
    uncertainty_before_json = Column(JSON, nullable=True)
    uncertainty_after_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    gaps = relationship("InformationGapModel", back_populates="plan", cascade="all, delete-orphan")
    candidates = relationship("ObservationCandidateModel", back_populates="plan", cascade="all, delete-orphan")
    outcomes = relationship("ObservationOutcomeModel", back_populates="plan", cascade="all, delete-orphan")


class InformationGapModel(Base):
    """First-class representation of identified information gaps (Section 6, 49)."""

    __tablename__ = "information_gaps_t114"

    gap_id = Column(String(64), primary_key=True)
    plan_id = Column(String(64), ForeignKey("observation_plans_t114.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    missing_information = Column(Text, nullable=False)
    affected_entity = Column(String(128), nullable=False, index=True)
    affected_state = Column(String(128), nullable=False, default="")
    why_it_matters = Column(Text, nullable=False, default="")
    dependent_decision_id = Column(String(64), nullable=True, index=True)
    severity = Column(String(32), nullable=False, default="MEDIUM")
    freshness_requirement_seconds = Column(Float, nullable=False, default=60.0)
    is_resolved_by_existing_data = Column(Boolean, nullable=False, default=False)
    existing_evidence_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    plan = relationship("ObservationPlanModel", back_populates="gaps")


class ObservationCandidateModel(Base):
    """Candidate observations for resolving information gaps (Section 11, 49)."""

    __tablename__ = "observation_candidates_t114"

    candidate_id = Column(String(64), primary_key=True)
    plan_id = Column(String(64), ForeignKey("observation_plans_t114.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    gap_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    target_source = Column(String(128), nullable=False)
    method = Column(String(32), nullable=False, default="PASSIVE")
    scope = Column(String(32), nullable=False, default="ENTITY")
    cost_json = Column(JSON, nullable=False)
    risk_json = Column(JSON, nullable=False)
    value_estimate_json = Column(JSON, nullable=True)
    is_selected = Column(Boolean, nullable=False, default=False, index=True)
    is_blocked = Column(Boolean, nullable=False, default=False)
    block_reason = Column(String(256), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    plan = relationship("ObservationPlanModel", back_populates="candidates")


class ObservationOutcomeModel(Base):
    """Outcomes and evidence items gathered from executed observations (Section 32, 49)."""

    __tablename__ = "observation_outcomes_t114"

    outcome_id = Column(String(64), primary_key=True)
    plan_id = Column(String(64), ForeignKey("observation_plans_t114.plan_id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(String(64), nullable=False, index=True)
    source = Column(String(128), nullable=False)
    method = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    provenance_hash = Column(String(64), nullable=False, default="")
    data_payload = Column(JSON, nullable=False)
    summary = Column(Text, nullable=False, default="")
    conflicts_with_existing = Column(Boolean, nullable=False, default=False)
    conflict_details = Column(Text, nullable=False, default="")
    observed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    plan = relationship("ObservationPlanModel", back_populates="outcomes")
    verification = relationship("ObservationVerificationModel", back_populates="outcome", uselist=False, cascade="all, delete-orphan")


class ObservationVerificationModel(Base):
    """Integrity verification of acquired observation evidence (Section 39, 49)."""

    __tablename__ = "observation_verifications_t114"

    verification_id = Column(String(64), primary_key=True)
    outcome_id = Column(String(64), ForeignKey("observation_outcomes_t114.outcome_id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="PENDING")
    source_authenticated = Column(Boolean, nullable=False, default=True)
    schema_valid = Column(Boolean, nullable=False, default=True)
    freshness_valid = Column(Boolean, nullable=False, default=True)
    tamper_free = Column(Boolean, nullable=False, default=True)
    auditor = Column(String(64), nullable=False, default="VerificationEngine")
    verification_notes = Column(Text, nullable=False, default="")
    verified_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    outcome = relationship("ObservationOutcomeModel", back_populates="verification")
