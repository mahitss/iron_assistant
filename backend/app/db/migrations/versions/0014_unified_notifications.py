"""Migration for Kairo Unified Notification, Communication, Delivery, Priority, and Alerting Layer (Task 34).

Revision ID: 0014_unified_notifications
Revises: 0013_identity_sessions_and_device_trust
Create Date: 2026-09-09 21:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_unified_notifications"
down_revision: str | None = "0013_identity_sessions_and_device_trust"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. unified_notifications table
    op.create_table(
        "unified_notifications",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="NORMAL"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_event_id", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("dedupe_key", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_unified_notifications_user_id", "unified_notifications", ["user_id"])
    op.create_index("ix_unified_notifications_status", "unified_notifications", ["status"])
    op.create_index("ix_unified_notifications_priority", "unified_notifications", ["priority"])
    op.create_index("ix_unified_notifications_type", "unified_notifications", ["type"])
    op.create_index("ix_unified_notifications_project_id", "unified_notifications", ["project_id"])
    op.create_index("ix_unified_notifications_task_id", "unified_notifications", ["task_id"])
    op.create_index("ix_unified_notifications_dedupe_key", "unified_notifications", ["dedupe_key"])
    op.create_index("ix_unified_notifications_user_status", "unified_notifications", ["user_id", "status"])

    # 2. notification_actions table
    op.create_table(
        "notification_actions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("notification_id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["notification_id"], ["unified_notifications.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notification_actions_notification_id", "notification_actions", ["notification_id"])
    op.create_index("ix_notification_actions_status", "notification_actions", ["status"])

    # 3. notification_deliveries table
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("notification_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["notification_id"], ["unified_notifications.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notification_deliveries_notification_id", "notification_deliveries", ["notification_id"])
    op.create_index("ix_notification_deliveries_user_id", "notification_deliveries", ["user_id"])

    # 4. notification_preferences table
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("enabled_channels", sa.JSON(), nullable=False, server_default=sa.text("'[\"WEB\"]'")),
        sa.Column("type_preferences", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("quiet_hours_start", sa.String(length=8), nullable=False, server_default="22:00"),
        sa.Column("quiet_hours_end", sa.String(length=8), nullable=False, server_default="08:00"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("digest_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("digest_frequency", sa.String(length=16), nullable=False, server_default="daily"),
        sa.Column("grouping_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("min_priority", sa.String(length=16), nullable=False, server_default="LOW"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("notification_deliveries")
    op.drop_table("notification_actions")
    op.drop_table("unified_notifications")
