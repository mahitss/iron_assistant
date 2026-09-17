"""SQLAlchemy models for Kairo Unified Commands, Structured Intents, Goals, and Motivation (Tasks 35 & 48)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CommandModel(Base):
    """Stores incoming normalized user commands across all interfaces (Web, Desktop, Voice, API)."""

    __tablename__ = "unified_commands"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    attachments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    source_interface: Mapped[str] = mapped_column(String(32), default="WEB", nullable=False)
    project_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    intents: Mapped[list["IntentModel"]] = relationship(
        "IntentModel",
        back_populates="command",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_unified_commands_user_created", "user_id", "created_at"),
    )


class IntentModel(Base):
    """Stores validated structured intents extracted from commands with ambiguity and risk metadata."""

    __tablename__ = "unified_intents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    command_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("unified_commands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    entities_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    references_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    target_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    constraints_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    requested_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    ambiguity_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    risk: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="READY", nullable=False)
    next_action: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    command: Mapped["CommandModel"] = relationship("CommandModel", back_populates="intents")

    __table_args__ = (
        Index("ix_unified_intents_user_type", "user_id", "type"),
        Index("ix_unified_intents_user_created", "user_id", "created_at"),
    )


class GoalModel(Base):
    """Persisted user desired outcome distinct from specific execution tasks (Spec 9, 10)."""

    __tablename__ = "user_goals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    desired_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    success_criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    scope_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    constraints_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    owner: Mapped[str] = mapped_column(String(64), default="user", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ObjectiveModel(Base):
    """Measurable sub-outcome contributing to an overarching user goal (Spec 11-14)."""

    __tablename__ = "intent_objectives"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    goal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_metric: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_value: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssumptionModel(Base):
    """Transparently tracked operational assumption (Spec 50-54)."""

    __tablename__ = "intent_assumptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="INFERRED", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    impact: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AmbiguityRecordModel(Base):
    """Detected ambiguity with candidates and resolution state (Spec 55-57)."""

    __tablename__ = "intent_ambiguities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    candidates: Mapped[list[Any]] = mapped_column(JSON, default=list)
    impact: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    level: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    resolution: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="UNRESOLVED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ClarificationModel(Base):
    """Targeted clarification query requiring user feedback before consequential actions (Spec 58-62)."""

    __tablename__ = "intent_clarifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_decision: Mapped[str] = mapped_column(String(256), nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    default_if_any: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class MotivationModel(Base):
    """Non-psychological functional motivation signal (Spec 76-80)."""

    __tablename__ = "intent_motivations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentGraphModel(Base):
    """Directed Acyclic Graph linking Intent -> Goal -> Objectives -> Constraints -> Tasks -> Outcomes (Spec 74)."""

    __tablename__ = "intent_graphs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    goal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    nodes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    edges: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


# ============================================================================
# Task 108: Autonomous Intent Understanding, Goal Inference & Semantics Tables
# ============================================================================

class UserRequestModel(Base):
    """Canonical request entity tracking user-submitted input (Task 108)."""

    __tablename__ = "user_requests"

    request_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="en", nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="DIRECT_USER", nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="DEFAULT", nullable=False)
    context_reference_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="RECEIVED", nullable=False, index=True)
    is_external_content: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_user_requests_user_created", "user_id", "created_at"),
    )


class RequestVersionModel(Base):
    """Immutable version history for updated or corrected requests (Task 108)."""

    __tablename__ = "request_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), ForeignKey("user_requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    change_reason: Mapped[str] = mapped_column(String(128), default="INITIAL", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AutonomousIntentModel(Base):
    """Autonomous Structured Intent with component confidence and non-goals (Task 108)."""

    __tablename__ = "autonomous_intents"

    intent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), ForeignKey("user_requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    parent_intent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dependency_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target: Mapped[str] = mapped_column(String(256), default="UNKNOWN", nullable=False)
    target_epistemic: Mapped[str] = mapped_column(String(32), default="EXPLICIT", nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="DEFAULT", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    user_visible_outcome: Mapped[str] = mapped_column(Text, default="", nullable=False)
    non_goals_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    external_effect: Mapped[str] = mapped_column(String(32), default="INTERNAL_ONLY", nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_epistemic: Mapped[str] = mapped_column(String(32), default="UNKNOWN", nullable=False)

    target_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    goal_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    constraint_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    deadline_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    scope_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    overall_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="UNDERSTOOD", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_superseded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class IntentCandidateModel(Base):
    """Candidate interpretations considered during interpretation (Task 108)."""

    __tablename__ = "intent_candidates"

    candidate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), ForeignKey("user_requests.request_id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentVersionModel(Base):
    """Immutable intent revision history (Task 108)."""

    __tablename__ = "intent_versions"

    version_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    intent_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reason_for_change: Mapped[str] = mapped_column(String(128), default="INITIAL", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class GoalHypothesisModel(Base):
    """Inferred goal hypotheses (Task 108)."""

    __tablename__ = "goal_hypotheses"

    hypothesis_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    evidence_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    assumptions_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    epistemic_status: Mapped[str] = mapped_column(String(32), default="INFERRED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DesiredOutcomeModel(Base):
    """Detailed desired outcome criteria (Task 108)."""

    __tablename__ = "desired_outcomes"

    outcome_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    observable_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    acceptance_criteria_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    quality_threshold: Mapped[str | None] = mapped_column(String(128), nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(String(64), default="DEFAULT", nullable=False)
    epistemic_status: Mapped[str] = mapped_column(String(32), default="INFERRED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentConstraintModel(Base):
    """Explicit and implicit constraints on intent (Task 108)."""

    __tablename__ = "intent_constraints"

    constraint_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    constraint_type: Mapped[str] = mapped_column(String(32), nullable=False)
    epistemic_strength: Mapped[str] = mapped_column(String(32), default="EXPLICIT", nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    parameter: Mapped[str | None] = mapped_column(String(128), nullable=True)
    value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="USER_INSTRUCTION", nullable=False)
    is_hard_constraint: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentPreferenceModel(Base):
    """User preferences differentiated by current vs historical scope (Task 108)."""

    __tablename__ = "intent_preferences"

    preference_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    is_current_request: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="EXPLICIT_USER", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentRequirementModel(Base):
    """Extracted quality and performance requirements (Task 108)."""

    __tablename__ = "intent_requirements"

    requirement_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_statement: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="USER_INSTRUCTION", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentAssumptionModelV2(Base):
    """Operational assumptions and safe defaults (Task 108)."""

    __tablename__ = "intent_assumptions_v2"

    assumption_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    assumption_type: Mapped[str] = mapped_column(String(32), default="SAFE_DEFAULT", nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="SYSTEM_DEFAULT", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.85, nullable=False)
    impact_level: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    is_reversible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentAmbiguityModelV2(Base):
    """Ambiguity items tracked with consequence levels (Task 108)."""

    __tablename__ = "intent_ambiguities_v2"

    ambiguity_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    ambiguity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    candidates_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    consequence_level: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    requires_user_clarification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentClarificationModelV2(Base):
    """Targeted clarification questions (Task 108)."""

    __tablename__ = "intent_clarifications_v2"

    clarification_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    ambiguity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    affected_decision: Mapped[str] = mapped_column(String(256), nullable=False)
    options_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    safe_default: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    user_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentEvidenceModel(Base):
    """Provenance-backed evidence items supporting intent formulation (Task 108)."""

    __tablename__ = "intent_evidence_items"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, default=0.9, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentConflictModel(Base):
    """Intent conflict records (Task 108)."""

    __tablename__ = "intent_conflicts"

    conflict_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    primary_intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    conflicting_intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(64), default="DIRECT_CONTRADICTION", nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentResolutionModel(Base):
    """Formal conflict or ambiguity resolution records (Task 108)."""

    __tablename__ = "intent_resolutions"

    resolution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    resolution_mechanism: Mapped[str] = mapped_column(String(64), nullable=False)
    resolved_value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentCorrectionModel(Base):
    """User correction records (Task 108)."""

    __tablename__ = "intent_corrections"

    correction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prior_intent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    revised_intent_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    scope_affected: Mapped[str] = mapped_column(String(64), default="CURRENT_PROJECT", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentFeedbackModel(Base):
    """Outcome and satisfaction feedback records (Task 108)."""

    __tablename__ = "intent_feedback_items"

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True)
    was_accurate: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_satisfaction_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntentSnapshotModel(Base):
    """Decision-time immutable snapshots (Task 108)."""

    __tablename__ = "intent_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    intent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    intent_data_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    goal_hypotheses_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    constraints_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    non_goals_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    assumptions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    external_effect: Mapped[str] = mapped_column(String(32), default="INTERNAL_ONLY", nullable=False)
    confidence_breakdown_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)


class IntentEventModel(Base):
    """Audit and telemetry event persistence (Task 108)."""

    __tablename__ = "intent_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    intent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), default="default_user", nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

