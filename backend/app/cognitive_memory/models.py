"""SQLAlchemy ORM models for Task 103: Cognitive Memory & Lifelong Learning Fabric."""

from __future__ import annotations

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


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _uuid_hex(prefix: str, length: int = 12) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:length]}"


class CognitiveExperienceModel(Base):
    """Stores captured operational experiences with strict trust classifications."""

    __tablename__ = "cognitive_experiences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("cexp"))
    experience_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scope: Mapped[str] = mapped_column(String(32), default="PROJECT", index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="kairo_system", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    structured_facts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), default="SUCCESS", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    trust_classification: Mapped[str] = mapped_column(String(64), default="OBSERVED", index=True, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    related_entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_missions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_situations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_decisions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_actions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    verification_references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    world_state_references: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class CognitiveMemoryModel(Base):
    """Durable long-term memory entity in the cognitive learning fabric."""

    __tablename__ = "cognitive_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("cmem"))
    memory_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    lifecycle_state: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PROJECT", index=True, nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    freshness: Mapped[str] = mapped_column(String(32), default="CURRENT", index=True, nullable=False)
    trust_classification: Mapped[str] = mapped_column(String(64), default="OBSERVED", index=True, nullable=False)

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supersedes: Mapped[str | None] = mapped_column(String(64), nullable=True)

    source_experience_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preconditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    procedure_steps: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    verification_criteria: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exceptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    application_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    useful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class CognitiveMemoryConflictModel(Base):
    """Stores dialectic contradictions and resolution states."""

    __tablename__ = "cognitive_memory_conflicts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("ccnf"))
    conflict_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_a_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    memory_b_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    memory_a_claim: Mapped[str] = mapped_column(Text, nullable=False)
    memory_b_claim: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PROJECT", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class CognitiveMemoryPatternModel(Base):
    """Stores recurrent pattern abstractions."""

    __tablename__ = "cognitive_memory_patterns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("cpat"))
    pattern_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    pattern_type: Mapped[str] = mapped_column(String(64), default="PATTERN", nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PROJECT", nullable=False)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    source_experience_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    exceptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class CognitiveMemoryFeedbackModel(Base):
    """Tracks application outcome feedback and error telemetry."""

    __tablename__ = "cognitive_memory_feedbacks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("cfbk"))
    feedback_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    application_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    was_useful: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    caused_error: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    empirical_outcome: Mapped[str] = mapped_column(String(64), default="SUCCESS", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
