"""SQLAlchemy database models for Kairo Resilience, Fault-Tolerance, and Recovery (Task 37)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid(prefix: str = "") -> str:
    u = uuid.uuid4().hex
    return f"{prefix}_{u[:12]}" if prefix else str(uuid.uuid4())


class IdempotencyModel(Base):
    """Tracks idempotency keys and cached execution results to prevent duplicate side effects."""

    __tablename__ = "resilience_idempotency"

    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="STARTED", nullable=False)
    result_reference: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)


class TaskLeaseModel(Base):
    """Distributed execution lease to prevent split-brain worker executions."""

    __tablename__ = "resilience_leases"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    worker_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fencing_token: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ResilienceCheckpointModel(Base):
    """Transactional, versioned task state checkpoints for crash recovery."""

    __tablename__ = "resilience_checkpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("ckpt"))
    task_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    policy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_resilience_checkpoints_task_created", "task_id", "created_at"),
    )


class QuarantineModel(Base):
    """Quarantined poison tasks that repeatedly failed or crashed."""

    __tablename__ = "resilience_quarantine"

    task_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    quarantined_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="QUARANTINED", nullable=False, index=True)
    quarantined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CircuitStateModel(Base):
    """Durable state persistence for distributed circuit breakers."""

    __tablename__ = "resilience_circuit_states"

    circuit_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    state: Mapped[str] = mapped_column(String(32), default="CLOSED", nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


# Task 76 Autonomous Resilience, Recovery, and Adaptive Defense Models
from app.resilience.defense_models import (  # noqa: E402
    AdaptiveDefenseRecommendationModel,
    PostIncidentLessonModel,
    RecoveryExecutionStepModel,
    RecoveryPlanModel,
    ResilienceAssessmentModel,
    ResilienceGapModel,
)

__all__ = [
    "IdempotencyModel",
    "TaskLeaseModel",
    "ResilienceCheckpointModel",
    "QuarantineModel",
    "CircuitStateModel",
    "ResilienceAssessmentModel",
    "ResilienceGapModel",
    "RecoveryPlanModel",
    "RecoveryExecutionStepModel",
    "PostIncidentLessonModel",
    "AdaptiveDefenseRecommendationModel",
]

