"""SQLAlchemy ORM models for Unified Observability, Traces, Spans, and Incidents (Task 38)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ObservabilityTraceModel(Base):
    """Stores distributed trace roots and execution outcomes."""

    __tablename__ = "observability_traces"

    trace_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    root_operation: Mapped[str] = mapped_column(String(128), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ObservabilitySpanModel(Base):
    """Stores individual execution spans within a distributed trace."""

    __tablename__ = "observability_spans"

    span_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    parent_span_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(128), nullable=False)
    component: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", index=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    attributes_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    events_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)


class ObservabilityIncidentModel(Base):
    """Stores operational incidents grouping correlated failures and anomalies."""

    __tablename__ = "observability_incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="MEDIUM", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    affected_components_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    root_cause_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
