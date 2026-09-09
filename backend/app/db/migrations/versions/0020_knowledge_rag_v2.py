"""Migration for Kairo Knowledge & Retrieval Intelligence Layer (RAG V2) (Task 40).

Revision ID: 0020_knowledge_rag_v2
Revises: 0019_unified_data_and_state_fabric
Create Date: 2026-09-10 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0020_knowledge_rag_v2"
down_revision: str | None = "0019_unified_data_and_state_fabric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. knowledge_chunks table
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False, server_default="PARAGRAPH"),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("headings", sa.JSON(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_id", sa.String(length=128), nullable=True),
        sa.Column("section_title", sa.String(length=256), nullable=True),
        sa.Column("start_time_seconds", sa.Float(), nullable=True),
        sa.Column("end_time_seconds", sa.Float(), nullable=True),
        sa.Column("speaker", sa.String(length=128), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("commit_hash", sa.String(length=64), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("freshness_state", sa.String(length=32), nullable=False, server_default="FRESH"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_chunks_user_doc", "knowledge_chunks", ["user_id", "document_id"])
    op.create_index("ix_knowledge_chunks_user_proj", "knowledge_chunks", ["user_id", "project_id"])
    op.create_index("ix_knowledge_chunks_source_type", "knowledge_chunks", ["source_type"])
    op.create_index("ix_knowledge_chunks_hash", "knowledge_chunks", ["content_hash"])

    # 2. knowledge_citations table
    op.create_table(
        "knowledge_citations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("query_id", sa.String(length=64), nullable=True),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("citation_label", sa.String(length=128), nullable=False),
        sa.Column("citation_text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_name", sa.String(length=256), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("line_range", sa.String(length=64), nullable=True),
        sa.Column("commit_hash", sa.String(length=64), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_citations_query", "knowledge_citations", ["query_id"])
    op.create_index("ix_knowledge_citations_user", "knowledge_citations", ["user_id"])

    # 3. code_symbols table
    op.create_table(
        "code_symbols",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("repo_id", sa.String(length=128), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("symbol_name", sa.String(length=256), nullable=False),
        sa.Column("symbol_type", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False, server_default="python"),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("signature", sa.String(length=512), nullable=True),
        sa.Column("docstring", sa.Text(), nullable=True),
        sa.Column("parent_symbol", sa.String(length=256), nullable=True),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_symbols_repo_file", "code_symbols", ["repo_id", "file_path"])
    op.create_index("ix_code_symbols_name", "code_symbols", ["symbol_name"])
    op.create_index("ix_code_symbols_user_proj", "code_symbols", ["user_id", "project_id"])

    # 4. code_dependencies table
    op.create_table(
        "code_dependencies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("repo_id", sa.String(length=128), nullable=False),
        sa.Column("source_file", sa.String(length=512), nullable=False),
        sa.Column("target_file", sa.String(length=512), nullable=False),
        sa.Column("source_symbol", sa.String(length=256), nullable=True),
        sa.Column("target_symbol", sa.String(length=256), nullable=True),
        sa.Column("dependency_type", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_deps_repo", "code_dependencies", ["repo_id"])
    op.create_index("ix_code_deps_source", "code_dependencies", ["source_file"])
    op.create_index("ix_code_deps_target", "code_dependencies", ["target_file"])


def downgrade() -> None:
    op.drop_table("code_dependencies")
    op.drop_table("code_symbols")
    op.drop_table("knowledge_citations")
    op.drop_table("knowledge_chunks")
