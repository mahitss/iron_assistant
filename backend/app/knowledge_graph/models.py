"""SQLAlchemy models for Kairo Personal Knowledge Graph & Relationship Memory Engine (Task 50)."""

from datetime import UTC, datetime
from typing import Any
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class NodeModel(Base):
    """Represents a node in the structured personal knowledge graph."""

    __tablename__ = "kg_nodes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    node_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    canonical_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PRIVATE", nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class EdgeModel(Base):
    """Represents a relationship edge between two nodes in the knowledge graph."""

    __tablename__ = "kg_edges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    source_node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relationship: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str] = mapped_column(String(32), default="PRIVATE", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AssertionModel(Base):
    """Represents a semantic triple assertion with temporal validity and confidence."""

    __tablename__ = "kg_assertions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    subject: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    predicate: Mapped[str] = mapped_column(String(128), nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    source_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PRIVATE", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class DecisionModel(Base):
    """Represents a durable architectural, technical, or project decision with rationale."""

    __tablename__ = "kg_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    question: Mapped[str] = mapped_column(String(512), nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    alternatives_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    rationale_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PROJECT", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class PreferenceModel(Base):
    """Represents durable or temporary preferences with override support."""

    __tablename__ = "kg_preferences"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    scope: Mapped[str] = mapped_column(String(32), default="PRIVATE", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_confirmed: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class OutcomeModel(Base):
    """Represents a verified or observed outcome tied to goals or workflows."""

    __tablename__ = "kg_outcomes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    related_goal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ContradictionModel(Base):
    """Represents detected conflicting assertions with provenance and resolution state."""

    __tablename__ = "kg_contradictions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    subject: Mapped[str] = mapped_column(String(256), nullable=False)
    conflicting_assertions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolution_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="DETECTED", nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
