"""SQLAlchemy persistence models for Kairo Autonomous Hypothesis, Experimentation & Scientific Discovery Engine (Task 72)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class DiscoverySessionModel(Base):
    """Persists high-level scientific discovery sessions and state."""

    __tablename__ = "discovery_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    discovery_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, default="default_user", nullable=False)

    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mission_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reasoning_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(Text, default="", nullable=False)
    domain: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="CREATED", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    conclusions_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    provenance_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_discovery_tenant_ws", "tenant_id", "workspace_id"),
        Index("ix_discovery_status", "status"),
    )


class ResearchQuestionModel(Base):
    """Persists formulated research questions."""

    __tablename__ = "discovery_questions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    discovery_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    question: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    uncertainty: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    goal_alignment: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    decision_relevance: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="OPEN", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DiscoveryHypothesisModel(Base):
    """Persists candidate hypotheses under investigation."""

    __tablename__ = "discovery_hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hypothesis_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    discovery_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    question_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    contradicting_evidence_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    falsification_criteria_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", nullable=False)
    plausibility: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    testability: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="autonomous_discovery", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExperimentModel(Base):
    """Persists planned and executed experiments."""

    __tablename__ = "discovery_experiments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    discovery_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    objective: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    experiment_type: Mapped[str] = mapped_column(String(32), default="OBSERVATIONAL", nullable=False)
    environment: Mapped[str] = mapped_column(String(32), default="STAGING", nullable=False)
    scope: Mapped[str] = mapped_column(String(64), default="isolated", nullable=False)

    independent_variables_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    dependent_variables_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    control_variables_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    potential_confounders_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    baseline_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, default="", nullable=False)
    success_criteria_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    failure_criteria_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    falsification_criteria_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    risk_level: Mapped[str] = mapped_column(String(32), default="LOW_RISK", nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    estimated_duration_sec: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    expected_information_gain: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)

    authorization_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    authorized_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    rollback_plan_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    cleanup_plan_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    dependencies_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    status: Mapped[str] = mapped_column(String(32), index=True, default="PROPOSED", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PredictionModel(Base):
    """Persists pre-execution predictions (immutable record)."""

    __tablename__ = "discovery_predictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    prediction_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    experiment_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    hypothesis_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    expected_direction: Mapped[str] = mapped_column(String(32), default="decrease", nullable=False)
    expected_range: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)
    assumptions_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ObservationModel(Base):
    """Persists empirical measurements captured during experiment runs."""

    __tablename__ = "discovery_observations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    observation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    experiment_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    source: Mapped[str] = mapped_column(String(128), nullable=False)
    environment: Mapped[str] = mapped_column(String(32), default="STAGING", nullable=False)
    measurement_metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    raw_reference: Mapped[str] = mapped_column(Text, default="", nullable=False)
    verification_state: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", nullable=False)
    is_simulation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExperimentResultModel(Base):
    """Persists analysis comparing predictions vs observations."""

    __tablename__ = "discovery_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    result_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    experiment_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    outcome: Mapped[str] = mapped_column(String(32), index=True, default="SUPPORTED", nullable=False)
    prediction_vs_observation_summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    effect_size: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unexpected_anomaly_detected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    new_hypotheses_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    invalidation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    replication_status: Mapped[str] = mapped_column(String(32), default="SINGLE_RUN", nullable=False)
    generalization_scope: Mapped[str] = mapped_column(
        String(32), default="ENVIRONMENT_SPECIFIC", nullable=False
    )
    conclusions_json: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DiscoveryAuditModel(Base):
    """Persists auditable scientific discovery events."""

    __tablename__ = "discovery_audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    discovery_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    experiment_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
