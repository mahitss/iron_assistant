"""SQLAlchemy data models for Kairo Knowledge Fabric.

Connects Projects, Conversations, Memories, Repositories, Documents, Web Research,
Workflow Runs, Notifications, Agent Tasks, Devices, Decisions, and provenance graph edges.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    """Generate timezone-aware UTC current timestamp."""
    return datetime.now(UTC)


class KnowledgeSourceModel(Base):
    """Provenance record tracking the authoritative origin of knowledge items."""

    __tablename__ = "knowledge_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    project_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_knowledge_sources_user_type", "user_id", "source_type"),
        Index("ix_knowledge_sources_user_proj", "user_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeSource(id='{self.id}', type='{self.source_type}', source_id='{self.source_id}')>"


class KnowledgeNodeModel(Base):
    """Normalized Knowledge Node abstraction indexing entities across the workspace."""

    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    node_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True, default=dict
    )

    # Relationships
    outgoing_edges: Mapped[list["KnowledgeEdgeModel"]] = relationship(
        "KnowledgeEdgeModel",
        foreign_keys="KnowledgeEdgeModel.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["KnowledgeEdgeModel"]] = relationship(
        "KnowledgeEdgeModel",
        foreign_keys="KnowledgeEdgeModel.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_knowledge_nodes_user_type", "user_id", "type"),
        Index("ix_knowledge_nodes_user_proj", "user_id", "project_id"),
        Index("ix_knowledge_nodes_user_status", "user_id", "status"),
        Index("ix_knowledge_nodes_created", "created_at"),
        Index("ix_knowledge_nodes_user_source", "user_id", "source_id"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeNode(id='{self.id}', type='{self.type}', title='{self.title[:30]}')>"


class KnowledgeEdgeModel(Base):
    """Directed, typed relationship edge connecting knowledge nodes."""

    __tablename__ = "knowledge_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String(128), default="SYSTEM_DERIVED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Node relationships
    source_node: Mapped["KnowledgeNodeModel"] = relationship(
        "KnowledgeNodeModel", foreign_keys=[source_node_id], back_populates="outgoing_edges"
    )
    target_node: Mapped["KnowledgeNodeModel"] = relationship(
        "KnowledgeNodeModel", foreign_keys=[target_node_id], back_populates="incoming_edges"
    )

    __table_args__ = (
        Index("ix_knowledge_edges_source_rel", "source_node_id", "relation_type"),
        Index("ix_knowledge_edges_target_rel", "target_node_id", "relation_type"),
        Index("ix_knowledge_edges_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeEdge(id='{self.id}', rel='{self.relation_type}', {self.source_node_id}->{self.target_node_id})>"


class KnowledgeIndexJobModel(Base):
    """Tracks background ingestion and backfill task lifecycle."""

    __tablename__ = "knowledge_index_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_knowledge_jobs_user_status", "user_id", "status"),
        Index("ix_knowledge_jobs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeIndexJob(id='{self.id}', type='{self.job_type}', status='{self.status}')>"
