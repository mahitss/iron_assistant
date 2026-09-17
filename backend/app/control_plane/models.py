"""SQLAlchemy models for persisting Control Plane cycles and snapshots (Task 102)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.session import Base

# Fallback JSON type for cross-dialect compatibility (PostgreSQL JSONB or standard JSON)
JSONType = JSONB().with_variant(JSON(), "sqlite")


class ControlCycleModel(Base):
    """Persistent audit record of an autonomous cognitive control cycle."""

    __tablename__ = "control_cycles"

    cycle_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=4, index=True)
    control_mode: Mapped[str] = mapped_column(String(32), default="BOUNDED_AUTONOMY", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    trigger_type: Mapped[str] = mapped_column(String(64), index=True)
    trigger_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    coalesced_triggers_json: Mapped[list[Any]] = mapped_column(JSONType, default=list)
    scope: Mapped[str] = mapped_column(String(64), default="SYSTEM", index=True)

    objective_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mission_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    situation_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    world_state_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    self_state_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)

    result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    waiting_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    no_action_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    budget_consumed_json: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)

    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True)
