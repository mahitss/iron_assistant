"""SQLAlchemy database models for Kairo Autonomous Task Engine (Task 31)."""

import uuid
from datetime import UTC, datetime
from typing import Any, List

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    """Generate timezone-aware UTC current timestamp."""
    return datetime.now(UTC)


def generate_uuid(prefix: str = "") -> str:
    """Generate a prefixed or raw UUID string."""
    u = uuid.uuid4().hex
    return f"{prefix}_{u[:12]}" if prefix else str(uuid.uuid4())


class TaskModel(Base):
    """Stores the authoritative record of an objective-oriented autonomous Task."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("task"))
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)  # Immutable original user objective
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="NORMAL", nullable=False)
    autonomy_level: Mapped[str] = mapped_column(String(32), default="SUPERVISED", nullable=False)
    parent_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True, default=lambda: generate_uuid("corr"), nullable=False)
    current_step_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    active_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    budget: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    plans: Mapped[List["TaskPlanModel"]] = relationship(
        "TaskPlanModel", back_populates="task", cascade="all, delete-orphan"
    )
    steps: Mapped[List["TaskStepModel"]] = relationship(
        "TaskStepModel", back_populates="task", cascade="all, delete-orphan"
    )
    checkpoints: Mapped[List["TaskCheckpointModel"]] = relationship(
        "TaskCheckpointModel", back_populates="task", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_tasks_user_status_model", "user_id", "status"),
    )


class TaskPlanModel(Base):
    """Represents a structured, versioned decomposition of an objective into a DAG of steps."""

    __tablename__ = "task_plans"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("plan"))
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    plan_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    steps_data: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    verification_criteria: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    supersedes_plan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    task: Mapped["TaskModel"] = relationship("TaskModel", back_populates="plans")
    steps: Mapped[List["TaskStepModel"]] = relationship(
        "TaskStepModel", back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_task_plans_task_version_model", "task_id", "version"),
    )


class TaskStepModel(Base):
    """An individual execution node in a task plan DAG."""

    __tablename__ = "task_steps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("step"))
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(64), ForeignKey("task_plans.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), default="READ", nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    approval_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    result_reference: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    task: Mapped["TaskModel"] = relationship("TaskModel", back_populates="steps")
    plan: Mapped["TaskPlanModel"] = relationship("TaskPlanModel", back_populates="steps")

    __table_args__ = (
        Index("ix_task_steps_task_seq_model", "task_id", "sequence"),
    )


class TaskCheckpointModel(Base):
    """Persists intermediate task state snapshots for safe crash resumption."""

    __tablename__ = "task_checkpoints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("ckpt"))
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    plan_version: Mapped[int] = mapped_column(Integer, nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    state_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    task: Mapped["TaskModel"] = relationship("TaskModel", back_populates="checkpoints")

    __table_args__ = (
        Index("ix_task_checkpoints_task_created_model", "task_id", "created_at"),
    )


class TaskLockModel(Base):
    """Expiring resource lock to prevent conflicting concurrent writes."""

    __tablename__ = "task_locks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: generate_uuid("lock"))
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(256), nullable=False)
    task_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_task_locks_res_model", "resource_type", "resource_id"),
    )
