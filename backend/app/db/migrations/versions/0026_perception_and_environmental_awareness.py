"""Migration for Perception, Environmental Awareness, Multi-Source Observation, and Change Detection (Task 46).

Revision ID: 0026_perception_awareness
Revises: 0025_autonomous_execution
Create Date: 2026-09-10 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_perception_awareness"
down_revision: str | None = "0025_autonomous_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. perception_sources
    op.create_table(
        "perception_sources",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("privacy_level", sa.String(length=32), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_perception_sources_type", "perception_sources", ["type"])
    op.create_index("ix_perception_sources_status", "perception_sources", ["status"])

    # 2. perception_observations
    op.create_table(
        "perception_observations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("payload_reference", sa.String(length=256), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("provenance_data", sa.JSON(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["perception_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_perception_observations_source_id", "perception_observations", ["source_id"])
    op.create_index("ix_perception_observations_subject", "perception_observations", ["subject"])
    op.create_index("ix_perception_observations_observed_at", "perception_observations", ["observed_at"])
    op.create_index("ix_perception_observations_correlation_id", "perception_observations", ["correlation_id"])
    op.create_index("ix_perception_obs_subj_time", "perception_observations", ["subject", "observed_at"])

    # 3. perception_change_events
    op.create_table(
        "perception_change_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("significance", sa.String(length=32), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=True),
        sa.Column("after_state", sa.JSON(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_perception_change_events_subject", "perception_change_events", ["subject"])
    op.create_index("ix_perception_change_events_change_type", "perception_change_events", ["change_type"])
    op.create_index("ix_perception_change_events_significance", "perception_change_events", ["significance"])
    op.create_index("ix_perception_change_events_environment", "perception_change_events", ["environment"])
    op.create_index("ix_perception_change_events_timestamp", "perception_change_events", ["timestamp"])

    # 4. perception_snapshots
    op.create_table(
        "perception_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("environment", sa.String(length=32), nullable=False),
        sa.Column("is_atomic", sa.Boolean(), nullable=False),
        sa.Column("devices", sa.JSON(), nullable=False),
        sa.Column("apps", sa.JSON(), nullable=False),
        sa.Column("services", sa.JSON(), nullable=False),
        sa.Column("repositories", sa.JSON(), nullable=False),
        sa.Column("deployments", sa.JSON(), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("agents", sa.JSON(), nullable=False),
        sa.Column("missing_sources", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_perception_snapshots_environment", "perception_snapshots", ["environment"])
    op.create_index("ix_perception_snap_env_ver", "perception_snapshots", ["environment", "version"], unique=True)

    # 5. perception_situations
    op.create_table(
        "perception_situations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("scope_data", sa.JSON(), nullable=False),
        sa.Column("observed_facts", sa.JSON(), nullable=False),
        sa.Column("inferences", sa.JSON(), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("anomalies", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("uncertainties", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_perception_situations_version", "perception_situations", ["version"])


def downgrade() -> None:
    op.drop_table("perception_situations")
    op.drop_table("perception_snapshots")
    op.drop_table("perception_change_events")
    op.drop_table("perception_observations")
    op.drop_table("perception_sources")
