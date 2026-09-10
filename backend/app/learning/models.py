"""SQLAlchemy database models for Kairo Adaptive Learning & Strategy Optimization (Task 43)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class LearningExperienceRecord(Base):
    """Stores structured task outcomes, verification results, and cost/duration metrics."""

    __tablename__ = "learning_experiences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experience_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    goal_type: Mapped[str] = mapped_column(String(64), index=True, default="GENERAL")
    plan_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    strategy: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    context_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actions: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    observations: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    verification_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    outcome: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # SUCCESS, FAILURE, etc.
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failures: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)

    __table_args__ = (
        Index("ix_learning_exp_outcome", "outcome", "created_at"),
        Index("ix_learning_exp_strategy", "strategy", "outcome"),
    )


class LearningSignalRecord(Base):
    """Quantified feedback or verification signals driving candidate improvements."""

    __tablename__ = "learning_signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    signal_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # verification, tool, user, test
    signal_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # POSITIVE, NEGATIVE, REGRESSION
    strength: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)  # 0.0 to 1.0
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True, nullable=False)


class LearningStrategyRecord(Base):
    """Governed execution or planning strategy with versioning and quality metrics."""

    __tablename__ = "learning_strategies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    prerequisites: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    expected_outcome: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    failure_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    verification_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True, nullable=False)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class LearningFailurePatternRecord(Base):
    """Recurring failure signatures, affected components, and recommended mitigations."""

    __tablename__ = "learning_failure_patterns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pattern_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    signature: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    affected_components: Mapped[dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    mitigation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="MEDIUM", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class LearningExperimentRecord(Base):
    """Controlled canary or A/B experiment comparing baseline vs candidate strategy."""

    __tablename__ = "learning_experiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PLANNED", index=True, nullable=False)
    baseline_strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_strategy_id: Mapped[str] = mapped_column(String(64), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LearningPromotionRecord(Base):
    """Append-only audit trail for strategy promotions and rollbacks."""

    __tablename__ = "learning_promotions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    promotion_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # PROMOTION, ROLLBACK
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


# =============================================================================
# TASK 52 CONTINUOUS LEARNING DATABASE MODELS
# =============================================================================

class LessonRecordModel(Base):
    """Stores extracted lessons with evidence links, scope, validity, and confidence."""

    __tablename__ = "learning_lessons"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    lesson_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    lesson_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_experiences: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    scope: Mapped[str] = mapped_column(String(64), index=True, default="PROJECT", nullable=False)
    validity: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="CANDIDATE", nullable=False)
    reinforcement_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    decay_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LearningOutcomeRecordModel(Base):
    """Tracks expected vs actual task outcomes and verification evidence."""

    __tablename__ = "learning_outcomes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    outcome_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    task_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    expected: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    actual: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    deviation: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    evidence_refs: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WorkflowPatternModel(Base):
    """Reusable multi-step workflows extracted from validated successes."""

    __tablename__ = "learning_workflows"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    preconditions: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    steps: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    expected_outcome: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    verification: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    failure_modes: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class HeuristicRecordModel(Base):
    """Operational heuristics for planning, routing, and tool selection."""

    __tablename__ = "learning_heuristics"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    heuristic_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    condition: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="TASK", index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ReplayRecordModel(Base):
    """Records offline simulation replays and temporal leakage checks."""

    __tablename__ = "learning_replays"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    replay_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    experience_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    simulated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    evaluation_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    temporal_cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    leakage_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LearningPolicyModel(Base):
    """Governed policies controlling what learning is permitted to adapt."""

    __tablename__ = "learning_policies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="GLOBAL", index=True, nullable=False)
    allowed_adaptations: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    rollback_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

