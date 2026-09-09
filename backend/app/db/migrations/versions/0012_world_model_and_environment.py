"""Migration for Kairo World Model, Live Environment State, and Entity Graph (Task 32).

Revision ID: 0012_world_model_and_environment
Revises: 0011_autonomous_task_engine
Create Date: 2026-09-09 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_world_model_and_environment"
down_revision: str | None = "0011_autonomous_task_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. world_entities table
    op.create_table(
        "world_entities",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=256), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=True),
        sa.Column("observation_type", sa.String(length=32), nullable=False, server_default="OBSERVED"),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="HIGH"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_world_entities_owner_type", "world_entities", ["owner_id", "type"])
    op.create_index("ix_world_entities_source", "world_entities", ["source", "source_id"])
    op.create_index("ix_world_entities_project", "world_entities", ["project_id"])
    op.create_index("ix_world_entities_type", "world_entities", ["type"])

    # 2. world_relationships table
    op.create_table(
        "world_relationships",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_entity_id", sa.String(length=64), nullable=False),
        sa.Column("target_entity_id", sa.String(length=64), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_world_rel_source_target", "world_relationships", ["source_entity_id", "target_entity_id"])
    op.create_index("ix_world_rel_owner", "world_relationships", ["owner_id"])
    op.create_index("ix_world_rel_type", "world_relationships", ["relationship_type"])

    # 3. world_observations table
    op.create_table(
        "world_observations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("raw_observation", sa.JSON(), nullable=False),
        sa.Column("observation_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_world_obs_entity", "world_observations", ["entity_id"])

    # 4. world_snapshots table
    op.create_table(
        "world_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("entities_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("relationships_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_world_snapshots_user", "world_snapshots", ["user_id"])
    op.create_index("ix_world_snapshots_project", "world_snapshots", ["project_id"])


def downgrade() -> None:
    op.drop_table("world_snapshots")
    op.drop_table("world_observations")
    op.drop_table("world_relationships")
    op.drop_table("world_entities")
