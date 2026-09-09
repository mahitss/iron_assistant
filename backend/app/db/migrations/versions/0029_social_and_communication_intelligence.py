"""Migration for Social and Communication Intelligence Engine (Task 49).

Revision ID: 0029_social_and_communication_intelligence
Revises: 0028_intent_goal_and_motivation
Create Date: 2026-09-10 05:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_social_and_communication_intelligence"
down_revision: str | None = "0028_intent_goal_and_motivation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. communication_channels
    op.create_table(
        "communication_channels",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("is_authorized", sa.Boolean(), nullable=False, default=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=16), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=16), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=False, default=30),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_channels_type", "communication_channels", ["channel_type"])

    # 2. communication_threads
    op.create_table(
        "communication_threads",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("channel_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("importance", sa.String(length=32), nullable=False, default="NORMAL"),
        sa.Column("participants_data", sa.JSON(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_threads_user_id", "communication_threads", ["user_id"])
    op.create_index("ix_comm_threads_state", "communication_threads", ["state"])
    op.create_index("ix_comm_threads_project_id", "communication_threads", ["project_id"])

    # 3. communication_messages
    op.create_table(
        "communication_messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("channel_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("sender_identity", sa.String(length=256), nullable=False),
        sa.Column("recipients_data", sa.JSON(), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False, default="INBOUND"),
        sa.Column("subject", sa.String(length=256), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("attachments_data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, default="DELIVERED"),
        sa.Column("provenance_data", sa.JSON(), nullable=False),
        sa.Column("privacy_scope", sa.String(length=32), nullable=False, default="PRIVATE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_messages_thread_id", "communication_messages", ["thread_id"])
    op.create_index("ix_comm_messages_user_id", "communication_messages", ["user_id"])
    op.create_index("ix_comm_messages_direction", "communication_messages", ["direction"])

    # 4. communication_relationships
    op.create_table(
        "communication_relationships",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("participant_identity", sa.String(length=256), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False, default="UNKNOWN"),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("communication_preferences", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, default=0.8),
        sa.Column("provenance_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_rel_user_id", "communication_relationships", ["user_id"])
    op.create_index("ix_comm_rel_participant", "communication_relationships", ["participant_identity"])

    # 5. communication_commitments
    op.create_table(
        "communication_commitments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=64), nullable=True),
        sa.Column("thread_id", sa.String(length=64), nullable=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, default="OPEN"),
        sa.Column("confidence", sa.Float(), nullable=False, default=0.9),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_commitments_user_id", "communication_commitments", ["user_id"])
    op.create_index("ix_comm_commitments_status", "communication_commitments", ["status"])

    # 6. communication_followups
    op.create_table(
        "communication_followups",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=False),
        sa.Column("trigger_type", sa.String(length=32), nullable=False, default="NO_RESPONSE"),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action_statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, default="OPEN"),
        sa.Column("attempts_count", sa.Integer(), nullable=False, default=0),
        sa.Column("max_attempts", sa.Integer(), nullable=False, default=3),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_followups_thread_id", "communication_followups", ["thread_id"])
    op.create_index("ix_comm_followups_user_id", "communication_followups", ["user_id"])

    # 7. communication_drafts
    op.create_table(
        "communication_drafts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.String(length=64), nullable=True),
        sa.Column("recipients_data", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(length=32), nullable=False, default="FORMAL"),
        sa.Column("intent_type", sa.String(length=32), nullable=False, default="REQUEST"),
        sa.Column("status", sa.String(length=32), nullable=False, default="DRAFT"),
        sa.Column("source_context", sa.JSON(), nullable=False),
        sa.Column("provenance_data", sa.JSON(), nullable=False),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, default=False),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comm_drafts_user_id", "communication_drafts", ["user_id"])
    op.create_index("ix_comm_drafts_status", "communication_drafts", ["status"])


def downgrade() -> None:
    op.drop_table("communication_drafts")
    op.drop_table("communication_followups")
    op.drop_table("communication_commitments")
    op.drop_table("communication_relationships")
    op.drop_table("communication_messages")
    op.drop_table("communication_threads")
    op.drop_table("communication_channels")
