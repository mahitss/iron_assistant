"""Migration for Kairo Unified Data & State Fabric, Durability, Consistency, Snapshots, and Changelog (Task 39).

Revision ID: 0019_unified_data_and_state_fabric
Revises: 0018_unified_observability
Create Date: 2026-09-10 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_unified_data_and_state_fabric"
down_revision: str | None = "0018_unified_observability"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. state_records table
    op.create_table(
        "state_records",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("classification", sa.String(length=32), nullable=False, server_default="AUTHORITATIVE"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("owner_domain", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain", "resource_type", "resource_id", name="uq_state_record_domain_resource"),
    )
    op.create_index("ix_state_records_domain", "state_records", ["domain"])
    op.create_index("ix_state_records_resource_type", "state_records", ["resource_type"])
    op.create_index("ix_state_records_resource_id", "state_records", ["resource_id"])
    op.create_index("ix_state_records_classification", "state_records", ["classification"])
    op.create_index("ix_state_records_user_id", "state_records", ["user_id"])
    op.create_index("ix_state_records_project_id", "state_records", ["project_id"])

    # 2. state_changelog table
    op.create_table(
        "state_changelog",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("service", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("changes_json", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_state_changelog_domain", "state_changelog", ["domain"])
    op.create_index("ix_state_changelog_resource_id", "state_changelog", ["resource_id"])
    op.create_index("ix_state_changelog_timestamp", "state_changelog", ["timestamp"])

    # 3. state_snapshots table
    op.create_table(
        "state_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("projection_identifier", sa.String(length=128), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_state_snapshots_projection_identifier", "state_snapshots", ["projection_identifier"])
    op.create_index("ix_state_snapshots_created_at", "state_snapshots", ["created_at"])

    # 4. state_locks table
    op.create_table(
        "state_locks",
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("owner", sa.String(length=64), nullable=False),
        sa.Column("fencing_token", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.create_index("ix_state_locks_expires_at", "state_locks", ["expires_at"])

    # 5. state_quarantine table
    op.create_table(
        "state_quarantine",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("quarantined_by", sa.String(length=64), nullable=False),
        sa.Column("quarantined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_state_quarantine_resource_id", "state_quarantine", ["resource_id"])


def downgrade() -> None:
    op.drop_table("state_quarantine")
    op.drop_table("state_locks")
    op.drop_table("state_snapshots")
    op.drop_table("state_changelog")
    op.drop_table("state_records")
