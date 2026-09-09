"""Migration for Kairo Knowledge Fabric.

Revision ID: 0008_knowledge_fabric
Revises: 0007_device_runtime
Create Date: 2026-09-09 11:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0008_knowledge_fabric"
down_revision: str | None = "0007_device_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. knowledge_sources
    op.create_table(
        "knowledge_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=256), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sources_user_id", "knowledge_sources", ["user_id"], unique=False)
    op.create_index("ix_knowledge_sources_source_type", "knowledge_sources", ["source_type"], unique=False)
    op.create_index("ix_knowledge_sources_source_id", "knowledge_sources", ["source_id"], unique=False)
    op.create_index("ix_knowledge_sources_project_id", "knowledge_sources", ["project_id"], unique=False)
    op.create_index("ix_knowledge_sources_user_type", "knowledge_sources", ["user_id", "source_type"], unique=False)
    op.create_index("ix_knowledge_sources_user_proj", "knowledge_sources", ["user_id", "project_id"], unique=False)

    # 2. knowledge_nodes
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=256), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_nodes_user_id", "knowledge_nodes", ["user_id"], unique=False)
    op.create_index("ix_knowledge_nodes_type", "knowledge_nodes", ["type"], unique=False)
    op.create_index("ix_knowledge_nodes_source_id", "knowledge_nodes", ["source_id"], unique=False)
    op.create_index("ix_knowledge_nodes_project_id", "knowledge_nodes", ["project_id"], unique=False)
    op.create_index("ix_knowledge_nodes_status", "knowledge_nodes", ["status"], unique=False)
    op.create_index("ix_knowledge_nodes_created_at", "knowledge_nodes", ["created_at"], unique=False)
    op.create_index("ix_knowledge_nodes_user_type", "knowledge_nodes", ["user_id", "type"], unique=False)
    op.create_index("ix_knowledge_nodes_user_proj", "knowledge_nodes", ["user_id", "project_id"], unique=False)
    op.create_index("ix_knowledge_nodes_user_status", "knowledge_nodes", ["user_id", "status"], unique=False)
    op.create_index("ix_knowledge_nodes_user_source", "knowledge_nodes", ["user_id", "source_id"], unique=False)

    # 3. knowledge_edges
    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("source_node_id", sa.String(length=36), nullable=False),
        sa.Column("target_node_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(length=128), nullable=False, server_default="SYSTEM_DERIVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["knowledge_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_edges_user_id", "knowledge_edges", ["user_id"], unique=False)
    op.create_index("ix_knowledge_edges_source_node_id", "knowledge_edges", ["source_node_id"], unique=False)
    op.create_index("ix_knowledge_edges_target_node_id", "knowledge_edges", ["target_node_id"], unique=False)
    op.create_index("ix_knowledge_edges_relation_type", "knowledge_edges", ["relation_type"], unique=False)
    op.create_index("ix_knowledge_edges_source_rel", "knowledge_edges", ["source_node_id", "relation_type"], unique=False)
    op.create_index("ix_knowledge_edges_target_rel", "knowledge_edges", ["target_node_id", "relation_type"], unique=False)

    # 4. knowledge_index_jobs
    op.create_table(
        "knowledge_index_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_jobs_user_id", "knowledge_index_jobs", ["user_id"], unique=False)
    op.create_index("ix_knowledge_jobs_job_type", "knowledge_index_jobs", ["job_type"], unique=False)
    op.create_index("ix_knowledge_jobs_status", "knowledge_index_jobs", ["status"], unique=False)
    op.create_index("ix_knowledge_jobs_user_status", "knowledge_index_jobs", ["user_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_table("knowledge_index_jobs")
    op.drop_table("knowledge_edges")
    op.drop_table("knowledge_nodes")
    op.drop_table("knowledge_sources")
