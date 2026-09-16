"""Autonomous system state graph, self-modeling and operational digital twin tables (Task 93).

Revision ID: 0061_autonomous_system_state_graph_and_self_modeling
Revises: 0060_autonomous_knowledge_consolidation_and_memory_evolution
Create Date: 2026-09-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0061_autonomous_system_state_graph_and_self_modeling"
down_revision: str | None = "0060_autonomous_knowledge_consolidation_and_memory_evolution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. System State Snapshots
    op.create_table(
        "system_state_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("schema_version", sa.String(length=32), server_default="v1", nullable=False),
        sa.Column("system_version", sa.String(length=32), server_default="0.93.0", nullable=False),
        sa.Column("source_event_watermark", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("state_hash", sa.String(length=128), nullable=False),
        sa.Column("entity_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("edge_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("entities_data", sa.JSON(), nullable=False),
        sa.Column("edges_data", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sys_snap_snapshot_id", "system_state_snapshots", ["snapshot_id"])
    op.create_index("ix_sys_snap_hash", "system_state_snapshots", ["state_hash"])
    op.create_index("ix_sys_snap_created", "system_state_snapshots", ["created_at"])
    op.create_index("ix_sys_snap_watermark", "system_state_snapshots", ["source_event_watermark"])

    # 2. System State Deltas
    op.create_table(
        "system_state_deltas",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("delta_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("from_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("to_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("delta_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("epistemic_status", sa.String(length=32), server_default="OBSERVED", nullable=False),
        sa.Column("affected_tasks", sa.JSON(), nullable=False),
        sa.Column("affected_workflows", sa.JSON(), nullable=False),
        sa.Column("affected_goals", sa.JSON(), nullable=False),
        sa.Column("affected_dependencies", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sys_delta_delta_id", "system_state_deltas", ["delta_id"])
    op.create_index("ix_sys_delta_from_to", "system_state_deltas", ["from_snapshot_id", "to_snapshot_id"])
    op.create_index("ix_sys_delta_entity", "system_state_deltas", ["entity_id", "delta_type"])
    op.create_index("ix_sys_delta_detected", "system_state_deltas", ["detected_at"])

    # 3. System State Reconciliations
    op.create_table(
        "system_state_reconciliations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("reconciliation_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("watermark_start", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("watermark_end", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("repaired_entities", sa.Integer(), server_default="0", nullable=False),
        sa.Column("orphaned_entities", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stale_entities", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="COMPLETED", nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sys_reconcile_rec_id", "system_state_reconciliations", ["reconciliation_id"])
    op.create_index("ix_sys_reconcile_created", "system_state_reconciliations", ["created_at"])
    op.create_index("ix_sys_reconcile_status", "system_state_reconciliations", ["status"])


def downgrade() -> None:
    op.drop_table("system_state_reconciliations")
    op.drop_table("system_state_deltas")
    op.drop_table("system_state_snapshots")
