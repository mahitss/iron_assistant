"""SQLAlchemy models for persisting Kairo Autonomous Self-Model snapshots and deltas (Task 101)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.session import Base

# Fallback JSON type for cross-dialect compatibility (PostgreSQL JSONB or standard JSON)
JSONType = JSONB().with_variant(JSON(), "sqlite")


class SelfModelSnapshotModel(Base):
    """Immutable persistent record of a self-state snapshot."""

    __tablename__ = "self_model_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    model_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    runtime_version: Mapped[str] = mapped_column(String(32), default="0.2.0")
    protocol_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    autonomy_mode: Mapped[str] = mapped_column(String(32), default="BOUNDED_AUTONOMY", index=True)
    emergency_stop_state: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)

    # Structured JSON payloads
    capabilities_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    tools_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    runtime_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    resources_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    security_governance_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    dependencies_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    limitations_payload: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    uncertainties_payload: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    active_missions_payload: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    active_situations_payload: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    answers_payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    evidence_references: Mapped[list[Any]] = mapped_column(JSONType, default=list)


class SelfModelDeltaModel(Base):
    """Persistent record of computed deltas between snapshots."""

    __tablename__ = "self_model_deltas"

    delta_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    base_snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    target_snapshot_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )

    changes_payload: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    added_limitations: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    resolved_limitations: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    added_uncertainties: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    resolved_uncertainties: Mapped[list[Any]] = mapped_column(JSONType, default=list)
