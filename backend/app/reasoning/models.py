"""SQLAlchemy persistence models for Kairo Autonomous Reasoning & Deliberation Engine (Task 71)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReasoningSessionModel(Base):
    """Persists high-level reasoning sessions and their configuration."""

    __tablename__ = "reasoning_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reasoning_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="default_user", nullable=False)

    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mission_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attention_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    intent: Mapped[str] = mapped_column(String(128), default="", nullable=False)

    depth: Mapped[str] = mapped_column(String(32), default="STANDARD", nullable=False)
    current_state: Mapped[str] = mapped_column(String(32), index=True, default="CREATED", nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    uncertainty_state: Mapped[str] = mapped_column(String(32), default="UNCERTAIN", nullable=False)

    budget_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    explanation_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_rsn_sess_tenant_state", "tenant_id", "current_state"),
        Index("ix_rsn_sess_attention", "tenant_id", "attention_id"),
    )


class ReasoningSubproblemModel(Base):
    """Hierarchical decomposition sub-problems with bounded depth."""

    __tablename__ = "reasoning_subproblems"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subproblem_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reasoning_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="NORMAL", nullable=False)
    depth_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    dependencies_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    required_evidence_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    hypotheses_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReasoningHypothesisModel(Base):
    """Candidate hypotheses with falsification conditions and evidence links."""

    __tablename__ = "reasoning_hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hypothesis_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reasoning_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    subproblem_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="internal", nullable=False)

    supporting_evidence_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    contradicting_evidence_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    falsification_conditions_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    counterarguments_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReasoningEvidenceItemModel(Base):
    """Empirical observations and verified facts attached to reasoning."""

    __tablename__ = "reasoning_evidence_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reasoning_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)

    source_type: Mapped[str] = mapped_column(String(64), default="observation", nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_summary: Mapped[str] = mapped_column(Text, nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), default="KNOWN_SOURCE", nullable=False)
    reliability: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    independence_group: Mapped[str] = mapped_column(String(64), default="default", nullable=False)
    verification_state: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", nullable=False)
    is_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    raw_data_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    conflicting_evidence_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReasoningAssumptionModel(Base):
    """Tracked assumptions with conclusion dependency tracking."""

    __tablename__ = "reasoning_assumptions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assumption_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reasoning_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", nullable=False)
    validation_source: Mapped[str | None] = mapped_column(String(128), nullable=True)

    dependent_conclusion_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReasoningConclusionModel(Base):
    """Synthesized conclusions with lifecycle status and verification references."""

    __tablename__ = "reasoning_conclusions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conclusion_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reasoning_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    subproblem_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PROVISIONAL", nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    uncertainty_state: Mapped[str] = mapped_column(String(32), default="KNOWN", nullable=False)
    falsification_tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    supporting_hypothesis_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    assumption_ids_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    counterarguments_addressed_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReasoningGraphModel(Base):
    """Graph structure containing questions, subproblems, hypotheses, evidence, and conclusions."""

    __tablename__ = "reasoning_graphs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    graph_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reasoning_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)

    nodes_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    edges_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class ReasoningTraceModel(Base):
    """Audit-safe milestone trace of reasoning execution without private chain-of-thought."""

    __tablename__ = "reasoning_traces"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    reasoning_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)

    events_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
