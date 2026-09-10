"""SQLAlchemy ORM models for Kairo Resource & Capability Orchestration Engine (Task 59)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CapabilityModel(Base):
    """Catalog of registered, verified system capabilities."""

    __tablename__ = "capabilities"

    capability_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    provider: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    reliability: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    supported_environments: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_resources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    verification_method: Mapped[str] = mapped_column(String(128), default="ASSERTION", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="AVAILABLE", index=True, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)


class ResourceModel(Base):
    """Managed compute, memory, storage, quota, and operational resources."""

    __tablename__ = "orchestration_resources"

    resource_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(128), default="SYSTEM", nullable=False)
    total_capacity: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    available_capacity: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    allocated_capacity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reserved_capacity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="units", nullable=False)
    environment: Mapped[str] = mapped_column(String(64), default="development", nullable=False)
    health: Mapped[str] = mapped_column(String(32), default="HEALTHY", nullable=False)
    cost_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    ownership: Mapped[str] = mapped_column(String(128), default="SYSTEM", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="AVAILABLE", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)

    reservations: Mapped[list[ResourceReservationModel]] = relationship(
        "ResourceReservationModel", back_populates="resource", cascade="all, delete-orphan"
    )


class ResourceReservationModel(Base):
    """Time-bounded resource reservations preventing oversubscription and starvation."""

    __tablename__ = "resource_reservations"

    reservation_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    resource_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("orchestration_resources.resource_id", ondelete="CASCADE"), index=True, nullable=False
    )
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    purpose: Mapped[str] = mapped_column(String(256), nullable=False)
    scope: Mapped[str] = mapped_column(String(128), default="GLOBAL", nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    authorization_signature: Mapped[str | None] = mapped_column(String(256), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    resource: Mapped[ResourceModel] = relationship("ResourceModel", back_populates="reservations")


class OrchestrationPlanModel(Base):
    """Master orchestration plan mapping tasks to capabilities, resources, and waves."""

    __tablename__ = "orchestration_plans"

    orchestration_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    strategic_plan_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    task_graph: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    execution_waves: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True, nullable=False)
    health: Mapped[str] = mapped_column(String(32), default="ON_TRACK", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)

    assignments: Mapped[list[TaskAssignmentModel]] = relationship(
        "TaskAssignmentModel", back_populates="orchestration_plan", cascade="all, delete-orphan"
    )


class TaskAssignmentModel(Base):
    """Specific task-to-provider assignment with required capabilities and resources."""

    __tablename__ = "task_assignments"

    assignment_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    orchestration_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("orchestration_plans.orchestration_id", ondelete="CASCADE"), index=True, nullable=False
    )
    task_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), default="TOOL", nullable=False)
    capability_id: Mapped[str] = mapped_column(String(64), nullable=False)
    allocated_resources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    required_permissions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ASSIGNED", nullable=False)
    rationale: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    fallback_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verification_criteria: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc, nullable=False)

    orchestration_plan: Mapped[OrchestrationPlanModel] = relationship(
        "OrchestrationPlanModel", back_populates="assignments"
    )


class OrchestrationRevisionModel(Base):
    """Immutable audit revision preserving historical orchestration snapshots."""

    __tablename__ = "orchestration_revisions"

    revision_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    parent_orchestration_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    diff_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class OrchestrationOutcomeModel(Base):
    """Post-execution verified outcome and calibration tracking."""

    __tablename__ = "orchestration_outcomes"

    outcome_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    orchestration_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    actual_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    actual_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    variance_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    lessons_learned: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
