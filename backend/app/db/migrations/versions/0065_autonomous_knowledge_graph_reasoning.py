"""Autonomous knowledge graph reasoning, graph memory, relationship intelligence and structured inference engine tables (Task 97).

Revision ID: 0065_autonomous_knowledge_graph_reasoning
Revises: 0064_autonomous_multi_agent_collaboration_and_swarm_orchestration
Create Date: 2026-09-17 02:40:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0065_autonomous_knowledge_graph_reasoning"
down_revision: str | None = "0064_autonomous_multi_agent_collaboration_and_swarm_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. kg_snapshots
    op.create_table(
        "kg_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_type", sa.String(length=32), server_default="CURRENT", nullable=False),
        sa.Column("node_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("edge_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("node_ids_json", sa.JSON(), nullable=False),
        sa.Column("edge_ids_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.String(length=64), server_default="default_user", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_kg_snapshots_id", "kg_snapshots", ["id"])
    op.create_index("ix_kg_snapshots_user_id", "kg_snapshots", ["user_id"])
    op.create_index("ix_kg_snapshots_type", "kg_snapshots", ["snapshot_type"])

    # 2. kg_conflict_records
    op.create_table(
        "kg_conflict_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("source_node_id", sa.String(length=64), nullable=False),
        sa.Column("target_node_id", sa.String(length=64), nullable=False),
        sa.Column("conflict_type", sa.String(length=64), server_default="DIRECT_CONTRADICTION", nullable=False),
        sa.Column("resolution_state", sa.String(length=32), server_default="UNRESOLVED", nullable=False),
        sa.Column("evidence_refs_json", sa.JSON(), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("user_id", sa.String(length=64), server_default="default_user", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_kg_conflict_records_id", "kg_conflict_records", ["id"])
    op.create_index("ix_kg_conflict_records_source", "kg_conflict_records", ["source_node_id"])
    op.create_index("ix_kg_conflict_records_target", "kg_conflict_records", ["target_node_id"])
    op.create_index("ix_kg_conflict_records_user", "kg_conflict_records", ["user_id"])
    op.create_index("ix_kg_conflict_records_state", "kg_conflict_records", ["resolution_state"])


def downgrade() -> None:
    op.drop_table("kg_conflict_records")
    op.drop_table("kg_snapshots")
