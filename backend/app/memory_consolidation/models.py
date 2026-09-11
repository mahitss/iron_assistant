"""SQLAlchemy ORM models for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Enforces persistent storage for:
- Durable memory entities with cognitive classification
- Lineage-preserving provenance records
- Contradiction and conflict detection state
- Consolidation clusters and higher-level abstractions
- Immutable lifecycle audit logs
"""

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


class DurableMemoryModel(Base):
    """Represents a validated or in-lifecycle durable memory entity (Spec 4)."""

    __tablename__ = "durable_memories"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("dm"))
    memory_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), default="default_user", index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    cognitive_type: Mapped[str] = mapped_column(String(32), default="MEMORY", index=True, nullable=False)
    memory_type: Mapped[str] = mapped_column(
        String(32), default="EPISODIC_MEMORY", index=True, nullable=False
    )
    abstraction_level: Mapped[str] = mapped_column(
        String(32), default="RAW_OBSERVATION", index=True, nullable=False
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    freshness: Mapped[str] = mapped_column(String(32), default="FRESH", index=True, nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), default="STANDARD", nullable=False)
    trust_level: Mapped[str] = mapped_column(String(32), default="UNVERIFIED", index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    supersedes: Mapped[str | None] = mapped_column(String(64), nullable=True)

    retention_policy: Mapped[str] = mapped_column(String(64), default="DEFAULT", nullable=False)
    access_policy: Mapped[str] = mapped_column(String(64), default="PROJECT_SCOPED", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    last_accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, index=True, nullable=False
    )
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_consolidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[str] = mapped_column(String(64), default="kairo_ingestion", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(64), default="kairo_ingestion", nullable=False)

    __table_args__ = (
        Index("ix_durable_mem_tenant_type_status", "tenant_id", "memory_type", "status"),
        Index("ix_durable_mem_tenant_user", "tenant_id", "user_id"),
        Index("ix_durable_mem_freshness_expires", "freshness", "expires_at"),
    )


class MemoryProvenanceModel(Base):
    """Lineage and derivation graph for memories (Spec 7, 19)."""

    __tablename__ = "memory_provenances"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("mprv"))
    provenance_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    source_type: Mapped[str] = mapped_column(String(64), default="direct_observation", nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    event_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    parent_memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    derived_from_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    related_memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    decision_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    goal_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    plan_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    incident_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    prediction_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    outcome_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    verification_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    generation_lineage: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_independent_source: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="kairo_system", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MemoryConflictModel(Base):
    """Tracks contradictions and opposing assertions (Spec 12)."""

    __tablename__ = "memory_conflicts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("mcnf"))
    conflict_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    memory_a_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    memory_b_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CONFLICTED", index=True, nullable=False)

    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    temporal_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    environment_context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    resolution_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_memory_conflicts_pair", "memory_a_id", "memory_b_id"),
        Index("ix_memory_conflicts_tenant_status", "tenant_id", "status"),
    )


class MemoryConsolidationModel(Base):
    """Records autonomous clustering and abstraction runs (Spec 9, 10)."""

    __tablename__ = "memory_consolidations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("mcns"))
    consolidation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    candidate_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    consolidated_memory_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    abstraction_level: Mapped[str] = mapped_column(String(32), nullable=False)
    suggested_summary: Mapped[str] = mapped_column(Text, nullable=False)
    common_entities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)

    validated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MemoryAuditLogModel(Base):
    """Immutable audit records for memory lifecycle operations (Spec 33)."""

    __tablename__ = "memory_audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("maud"))
    audit_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(64), default="system", nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now_utc, index=True, nullable=False
    )
