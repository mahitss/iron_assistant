"""SQLAlchemy ORM models for Task 92: KAIRO Knowledge Consolidation & Memory Evolution.

Integrates with existing durable_memories, memory_provenances, and kg_nodes without duplication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

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


class MemoryEvidenceModel(Base):
    """Grounding evidence record supporting, contradicting, or qualifying a memory (Phase 4)."""

    __tablename__ = "memory_evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("m_evi"))
    evidence_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    relation_type: Mapped[str] = mapped_column(String(32), default="SUPPORT", index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(256), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), default="OBSERVED", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    reliability: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    freshness: Mapped[str] = mapped_column(String(32), default="FRESH", nullable=False)
    provenance_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_mem_evi_mem_relation", "memory_id", "relation_type"),
        Index("ix_mem_evi_tenant", "tenant_id"),
    )


class MemoryHypothesisModel(Base):
    """Tentative empirical claim tracked under validation (Phase 16)."""

    __tablename__ = "memory_hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("m_hyp"))
    hypothesis_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    claim: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED", index=True, nullable=False)
    validation_plan: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    supporting_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contradicting_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MemoryProceduralModel(Base):
    """Actionable workflow or recipe representation (Phase 14)."""

    __tablename__ = "memory_procedural"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("m_prc"))
    procedure_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    prerequisites: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    steps: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    expected_outputs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    failure_conditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    validation_history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    last_successful_execution_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capability_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MemoryDerivedLinkModel(Base):
    """Directed dependency graph for derived facts to cascade invalidation (Phase 17)."""

    __tablename__ = "memory_derived_links"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("m_drv"))
    derived_memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    parent_memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    derivation_method: Mapped[str] = mapped_column(String(128), default="deductive_inference", nullable=False)
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    invalidation_propagated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)

    __table_args__ = (
        Index("ix_mem_derived_pair", "derived_memory_id", "parent_memory_id"),
    )


class MemoryRevalidationJobModel(Base):
    """Resource-bounded autonomous revalidation candidates and outcomes (Phase 22)."""

    __tablename__ = "memory_revalidation_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("m_rev"))
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    trigger_reason: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED", index=True, nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)


class MemoryRetentionDecisionModel(Base):
    """Auditable retention decisions generated by the retention evaluator (Phase 12)."""

    __tablename__ = "memory_retention_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: _uuid_hex("m_rtd"))
    decision_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    memory_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True, nullable=False)

    action: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    utility_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    storage_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, nullable=False)
