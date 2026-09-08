"""Migration for proactive insights, settings, web monitors, and notification updates.

Revision ID: 0004_proactive
Revises: 0003_security
Create Date: 2026-09-08 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_proactive"
down_revision: str | None = "0003_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. proactive_insights
    op.create_table(
        "proactive_insights",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("actionability", sa.String(length=32), nullable=False, server_default="INFORMATIONAL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("action_payload", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_proactive_insights_user_id", "proactive_insights", ["user_id"], unique=False)
    op.create_index("ix_proactive_insights_source_type", "proactive_insights", ["source_type"], unique=False)
    op.create_index("ix_proactive_insights_status", "proactive_insights", ["status"], unique=False)
    op.create_index("ix_proactive_insights_priority", "proactive_insights", ["priority"], unique=False)
    op.create_index("ix_proactive_insights_fingerprint", "proactive_insights", ["fingerprint"], unique=False)
    op.create_index(
        "ix_proactive_insights_user_status", "proactive_insights", ["user_id", "status"], unique=False
    )
    op.create_index(
        "ix_proactive_insights_user_priority", "proactive_insights", ["user_id", "priority"], unique=False
    )
    op.create_index(
        "ix_proactive_insights_user_fingerprint",
        "proactive_insights",
        ["user_id", "fingerprint"],
        unique=False,
    )

    # 2. proactive_settings
    op.create_table(
        "proactive_settings",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("proactive_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_on_workflow_failure", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_on_ci_failure", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_on_approval", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notify_on_web_change", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("minimum_priority", sa.String(length=32), nullable=False, server_default="LOW"),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("quiet_hours_start", sa.String(length=16), nullable=False, server_default="22:00"),
        sa.Column("quiet_hours_end", sa.String(length=16), nullable=False, server_default="08:00"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # 3. web_monitors
    op.create_table(
        "web_monitors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("check_interval_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("content_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_monitors_user_id", "web_monitors", ["user_id"], unique=False)
    op.create_index("ix_web_monitors_user_enabled", "web_monitors", ["user_id", "enabled"], unique=False)

    # 4. update notifications table with dismissed and link columns
    op.add_column(
        "notifications", sa.Column("dismissed", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.add_column("notifications", sa.Column("link", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("notifications", "link")
    op.drop_column("notifications", "dismissed")
    op.drop_table("web_monitors")
    op.drop_table("proactive_settings")
    op.drop_table("proactive_insights")
