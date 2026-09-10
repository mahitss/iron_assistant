"""SQLAlchemy ORM models for Knowledge Synthesis & Research Intelligence Engine (Task 63)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

JSON_TYPE = JSONB().with_variant(Text, "sqlite")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class ResearchSessionModel(Base):
    __tablename__ = "research_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    objective: Mapped[str] = mapped_column(String(255), default="Knowledge Synthesis")
    scope: Mapped[str] = mapped_column(String(64), default="global")
    mode: Mapped[str] = mapped_column(String(32), default="STANDARD")
    status: Mapped[str] = mapped_column(String(32), default="COMPLETED")
    quality_score: Mapped[float] = mapped_column(Float, default=0.85)
    summary: Mapped[str] = mapped_column(Text, default="")
    tenant_id: Mapped[str] = mapped_column(String(64), default="default", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc, onupdate=_now_utc)


class ResearchSourceModel(Base):
    __tablename__ = "research_sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), default="Unknown")
    author: Mapped[str] = mapped_column(String(255), default="Unknown")
    url_or_reference: Mapped[str] = mapped_column(Text, nullable=False)
    authority_score: Mapped[float] = mapped_column(Float, default=0.5)
    freshness_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_retracted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class ResearchDocumentModel(Base):
    __tablename__ = "research_documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    format: Mapped[str] = mapped_column(String(32), default="markdown")
    content_hash: Mapped[str] = mapped_column(String(128), default="")
    raw_content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class ResearchClaimModel(Base):
    __tablename__ = "research_claims"

    claim_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    predicate: Mapped[str] = mapped_column(String(255), nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(64), default="REPORTED")
    confidence: Mapped[str] = mapped_column(String(32), default="MODERATE")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class ResearchEvidenceModel(Base):
    __tablename__ = "research_evidence"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    claim_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    excerpt_reference: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), default="PRIMARY_DOCUMENT")
    strength: Mapped[str] = mapped_column(String(32), default="MODERATE")
    directness: Mapped[str] = mapped_column(String(32), default="DIRECT")
    independence_score: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class ResearchConflictModel(Base):
    __tablename__ = "research_conflicts"

    conflict_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    claim_a_id: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_b_id: Mapped[str] = mapped_column(String(64), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="UNRESOLVED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class ResearchGapModel(Base):
    __tablename__ = "research_gaps"

    gap_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(32), default="HIGH")
    impact: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)


class ResearchAuditModel(Base):
    __tablename__ = "research_audits"

    sequence_number: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    claim_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now_utc)
