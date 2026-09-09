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
    Integer,
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


class KnowledgeChunkModel(Base):
    """Fine-grained semantic chunk representation for RAG V2."""

    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), default="PARAGRAPH", nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    headings: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    start_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    end_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    commit_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    freshness_state: Mapped[str] = mapped_column(String(32), default="FRESH", nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata_json", JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    __table_args__ = (
        Index("ix_knowledge_chunks_user_doc", "user_id", "document_id"),
        Index("ix_knowledge_chunks_user_proj", "user_id", "project_id"),
        Index("ix_knowledge_chunks_source_type", "source_type"),
        Index("ix_knowledge_chunks_hash", "content_hash"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeChunk(id='{self.id}', doc='{self.document_id}', type='{self.content_type}')>"


class KnowledgeCitationModel(Base):
    """Verified citation record mapping grounded answers to authoritative sources."""

    __tablename__ = "knowledge_citations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    query_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    chunk_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    citation_label: Mapped[str] = mapped_column(String(128), nullable=False)
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line_range: Mapped[str | None] = mapped_column(String(64), nullable=True)
    commit_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_knowledge_citations_query", "query_id"),
        Index("ix_knowledge_citations_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeCitation(id='{self.id}', label='{self.citation_label}', chunk='{self.chunk_id}')>"


class CodeSymbolModel(Base):
    """AST-extracted code symbol (function, class, module, imports)."""

    __tablename__ = "code_symbols"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    symbol_name: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    symbol_type: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(64), default="python", nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[str | None] = mapped_column(String(512), nullable=True)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_symbol: Mapped[str | None] = mapped_column(String(256), nullable=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_code_symbols_repo_file", "repo_id", "file_path"),
        Index("ix_code_symbols_name", "symbol_name"),
        Index("ix_code_symbols_user_proj", "user_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<CodeSymbol(id='{self.id}', name='{self.symbol_name}', type='{self.symbol_type}')>"


class CodeDependencyModel(Base):
    """Dependency graph connection between files, modules, and symbols."""

    __tablename__ = "code_dependencies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    repo_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    source_file: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    target_file: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    source_symbol: Mapped[str | None] = mapped_column(String(256), nullable=True)
    target_symbol: Mapped[str | None] = mapped_column(String(256), nullable=True)
    dependency_type: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        Index("ix_code_deps_repo", "repo_id"),
        Index("ix_code_deps_source", "source_file"),
        Index("ix_code_deps_target", "target_file"),
    )

    def __repr__(self) -> str:
        return f"<CodeDependency(repo='{self.repo_id}', {self.source_file}->{self.target_file})>"

