"""Migration for Kairo Unified Event Bus, Outbox, and Dead-Letter Queue.

Revision ID: 0009_unified_event_bus
Revises: 0008_knowledge_fabric
Create Date: 2026-09-09 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_unified_event_bus"
down_revision: str | None = "0008_knowledge_fabric"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. events table
    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_version", sa.String(length=16), nullable=False, server_default="v1"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("causation_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PUBLISHED"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_type_timestamp", "events", ["event_type", "timestamp"])
    op.create_index("ix_events_user_timestamp", "events", ["user_id", "timestamp"])
    op.create_index("ix_events_correlation", "events", ["correlation_id"])
    op.create_index(op.f("ix_events_event_type"), "events", ["event_type"])
    op.create_index(op.f("ix_events_user_id"), "events", ["user_id"])
    op.create_index(op.f("ix_events_project_id"), "events", ["project_id"])

    # 2. event_outbox table
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("event_data_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_event_outbox_status_created", "event_outbox", ["status", "created_at"])
    op.create_index(op.f("ix_event_outbox_event_id"), "event_outbox", ["event_id"])
    op.create_index(op.f("ix_event_outbox_event_type"), "event_outbox", ["event_type"])
    op.create_index(op.f("ix_event_outbox_status"), "event_outbox", ["status"])

    # 3. dead_letter_events table
    op.create_table(
        "dead_letter_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("handler_name", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("replay_safety", sa.String(length=32), nullable=False, server_default="REPLAY_REQUIRES_REVIEW"),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replayed_by", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dead_letter_events_event_id"), "dead_letter_events", ["event_id"])
    op.create_index(op.f("ix_dead_letter_events_event_type"), "dead_letter_events", ["event_type"])
    op.create_index(op.f("ix_dead_letter_events_user_id"), "dead_letter_events", ["user_id"])


def downgrade() -> None:
    op.drop_table("dead_letter_events")
    op.drop_table("event_outbox")
    op.drop_table("events")
