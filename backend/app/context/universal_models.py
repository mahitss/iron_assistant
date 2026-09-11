"""SQLAlchemy persistence models for Universal Context & Adaptive Personalization Engine (Task 69)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class AdaptivePreferenceModel(Base):
    """Stores user operational preferences with confidence, decay, and provenance tracking."""

    __tablename__ = "adaptive_preferences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    preference_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="INFERRED_PREFERENCE", nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    occurrences: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    last_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_adaptive_pref_user_cat_key", "tenant_id", "user_id", "category", "key"),)


class ContextSnapshotModel(Base):
    """Immutable audit records of assembled context for reproducibility, replay, and evaluation."""

    __tablename__ = "context_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    snapshot_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    goal_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    environment: Mapped[str | None] = mapped_column(String(64), nullable=True)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    selected_items_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    retrieval_reasons_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    missing_context_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    conflicts_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContextFeedbackModel(Base):
    """Records feedback on whether retrieved context elements were useful, ignored, or misleading."""

    __tablename__ = "context_feedback_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    feedback_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    context_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True, default="default", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    items_used: Mapped[Any] = mapped_column(JSON, nullable=False)
    items_ignored: Mapped[Any] = mapped_column(JSON, nullable=False)
    items_misleading: Mapped[Any] = mapped_column(JSON, nullable=False)
    items_missing: Mapped[Any] = mapped_column(JSON, nullable=False)
    retrieval_latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    task_outcome: Mapped[str] = mapped_column(String(64), default="SUCCESS", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
