"""Migration for Environmental Intelligence & Digital Twin Engine (Task 54).

Revision ID: 0034_environmental_intelligence_and_digital_twin
Revises: 0033_executive_memory_and_long_horizon_context
Create Date: 2026-09-14 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_environmental_intelligence_and_digital_twin"
down_revision: str | None = "0033_executive_memory_and_long_horizon_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. digital_twins
    op.create_table(
        "digital_twins",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("twin_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="SYSTEM"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("edges", sa.JSON(), nullable=False),
        sa.Column("health", sa.JSON(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("freshness", sa.String(length=64), nullable=False, server_default="FRESH"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("twin_id"),
    )
    op.create_index("ix_digital_twins_scope", "digital_twins", ["scope", "scope_id"])
    op.create_index("ix_digital_twins_timestamp", "digital_twins", ["timestamp"])

    # 2. environment_nodes
    op.create_table(
        "environment_nodes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("node_type", sa.String(length=64), nullable=False),
        sa.Column("canonical_id", sa.String(length=256), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("node_metadata", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="SYSTEM"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="UNKNOWN"),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id"),
    )
    op.create_index("ix_environment_nodes_canonical_id", "environment_nodes", ["canonical_id"])
    op.create_index("ix_environment_nodes_type_scope", "environment_nodes", ["node_type", "scope", "scope_id"])
    op.create_index("ix_environment_nodes_last_seen", "environment_nodes", ["last_seen"])

    # 3. environment_edges
    op.create_table(
        "environment_edges",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("edge_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("relationship", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.String(length=64), nullable=False, server_default="OBSERVED"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="ACTIVE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edge_id"),
    )
    op.create_index("ix_environment_edges_source_target", "environment_edges", ["source", "relationship", "target"])
    op.create_index("ix_environment_edges_status", "environment_edges", ["status"])

    # 4. environment_drifts
    op.create_table(
        "environment_drifts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("drift_id", sa.String(length=64), nullable=False),
        sa.Column("resource", sa.String(length=128), nullable=False),
        sa.Column("drift_type", sa.String(length=64), nullable=False),
        sa.Column("expected", sa.JSON(), nullable=False),
        sa.Column("actual", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False, server_default="MEDIUM"),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="DETECTED"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drift_id"),
    )
    op.create_index("ix_environment_drifts_resource", "environment_drifts", ["resource"])
    op.create_index("ix_environment_drifts_type_status", "environment_drifts", ["drift_type", "status"])

    # 5. environment_changes
    op.create_table(
        "environment_changes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("change_id", sa.String(length=64), nullable=False),
        sa.Column("resource", sa.String(length=128), nullable=False),
        sa.Column("change_type", sa.String(length=64), nullable=False),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("significance", sa.String(length=64), nullable=False, server_default="LOW"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("verification", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("change_id"),
    )
    op.create_index("ix_environment_changes_resource", "environment_changes", ["resource"])
    op.create_index("ix_environment_changes_timestamp", "environment_changes", ["timestamp"])

    # 6. environment_incidents
    op.create_table(
        "environment_incidents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="SYSTEM"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False, server_default="MEDIUM"),
        sa.Column("symptoms", sa.JSON(), nullable=False),
        sa.Column("affected_resources", sa.JSON(), nullable=False),
        sa.Column("suspected_cause", sa.String(length=256), nullable=True),
        sa.Column("root_cause", sa.String(length=256), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="DETECTED"),
        sa.Column("timeline", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id"),
    )
    op.create_index("ix_environment_incidents_scope", "environment_incidents", ["scope", "scope_id"])
    op.create_index("ix_environment_incidents_status", "environment_incidents", ["status"])

    # 7. environment_snapshots
    op.create_table(
        "environment_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="SYSTEM"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("edges", sa.JSON(), nullable=False),
        sa.Column("health_summary", sa.JSON(), nullable=False),
        sa.Column("freshness", sa.String(length=64), nullable=False, server_default="FRESH"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id"),
    )
    op.create_index("ix_environment_snapshots_scope", "environment_snapshots", ["scope", "scope_id"])
    op.create_index("ix_environment_snapshots_timestamp", "environment_snapshots", ["timestamp"])


def downgrade() -> None:
    op.drop_table("environment_snapshots")
    op.drop_table("environment_incidents")
    op.drop_table("environment_changes")
    op.drop_table("environment_drifts")
    op.drop_table("environment_edges")
    op.drop_table("environment_nodes")
    op.drop_table("digital_twins")
