"""SQLAlchemy ORM models for Task 112:
KAIRO Autonomous Causal Explanation, Event Chain Reconstruction, Root-Cause Analysis & "Why Did This Happen?" Engine.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class CausalExplanationModel(Base):
    """Authoritative persistent record of a structured causal explanation."""

    __tablename__ = "causal_explanations_t112"

    explanation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    target_entity: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_event_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    target_state_change: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(String(32), index=True, nullable=False, default="REQUESTED")

    # Structured 6-Part Narrative
    what_happened: Mapped[str] = mapped_column(Text, default="", nullable=False)
    what_changed: Mapped[str] = mapped_column(Text, default="", nullable=False)
    what_preceded_it: Mapped[str] = mapped_column(Text, default="", nullable=False)
    why_it_happened: Mapped[str] = mapped_column(Text, default="CAUSE UNKNOWN", nullable=False)
    contributing_factors_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    what_would_verify_this: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Deep Causal Structures
    root_cause_category: Mapped[str] = mapped_column(String(64), index=True, default="UNKNOWN", nullable=False)
    primary_cause: Mapped[str | None] = mapped_column(String(256), nullable=True)
    primary_mechanism: Mapped[str | None] = mapped_column(Text, nullable=True)

    causal_links_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    contributors_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    event_chain_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    alternatives_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    counterfactuals_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    unresolved_gaps_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    # Confidence & Calibration Breakdown
    confidence_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    quality_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    composite_confidence: Mapped[float] = mapped_column(Float, default=0.5, index=True, nullable=False)

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_cause_unknown: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    scope: Mapped[str] = mapped_column(String(64), default="DEFAULT", index=True, nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_expl_target_stage", "target_entity", "lifecycle_stage"),
        Index("ix_expl_created_at", "created_at"),
    )


class CausalHypothesisModel(Base):
    """Persistent candidate causal hypothesis with supporting and contradicting points."""

    __tablename__ = "causal_hypotheses_t112"

    hypothesis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    explanation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    hypothesis_summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_cause: Mapped[str] = mapped_column(String(256), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="POSSIBLE", index=True, nullable=False)

    supporting_points_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    contradicting_points_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    missing_evidence_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    discriminating_observation: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CausalLinkModel(Base):
    """Directional causal link step with mechanism and validation state."""

    __tablename__ = "causal_links_t112"

    link_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    explanation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_node: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    target_node: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    relationship_role: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True, nullable=False)
    mechanism: Mapped[str] = mapped_column(Text, default="", nullable=False)
    lag_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_temporally_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    confidence_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    supporting_evidence_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    contradicting_evidence_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    assumptions_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_clink_source_target", "source_node", "target_node"),
    )


class ExplanationVerificationModel(Base):
    """Empirical post-explanation verification test records."""

    __tablename__ = "explanation_verifications_t112"

    verification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    explanation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tested_hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_consequence: Mapped[str] = mapped_column(Text, nullable=False)
    actual_observation: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), index=True, default="UNRESOLVED", nullable=False)
    observation_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    verified_by_actor: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
