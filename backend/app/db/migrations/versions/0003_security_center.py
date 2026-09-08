"""Migration for Security Center: sessions, approvals, audit events, and user capabilities.

Revision ID: 0003_security
Revises: 0002_automation
Create Date: 2026-09-08 18:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_security"
down_revision: str | None = "0002_automation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. security_sessions
    op.create_table(
        "security_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_sessions_user_id", "security_sessions", ["user_id"], unique=False)
    op.create_index(
        "ix_security_sessions_user_active", "security_sessions", ["user_id", "is_active"], unique=False
    )

    # 2. security_approval_requests
    op.create_table(
        "security_approval_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=True),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False, server_default="HIGH"),
        sa.Column("arguments_summary", sa.JSON(), nullable=False),
        sa.Column("action_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_approvals_user_id", "security_approval_requests", ["user_id"], unique=False)
    op.create_index(
        "ix_security_approvals_tool_name", "security_approval_requests", ["tool_name"], unique=False
    )
    op.create_index("ix_security_approvals_status", "security_approval_requests", ["status"], unique=False)
    op.create_index(
        "ix_security_approvals_expires_at", "security_approval_requests", ["expires_at"], unique=False
    )
    op.create_index(
        "ix_security_approvals_action_fingerprint",
        "security_approval_requests",
        ["action_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_security_approvals_user_status", "security_approval_requests", ["user_id", "status"], unique=False
    )
    op.create_index(
        "ix_security_approvals_fingerprint_status",
        "security_approval_requests",
        ["action_fingerprint", "status"],
        unique=False,
    )

    # 3. security_audit_events
    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=True),
        sa.Column("risk_level", sa.String(length=32), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_audit_user_id", "security_audit_events", ["user_id"], unique=False)
    op.create_index("ix_security_audit_session_id", "security_audit_events", ["session_id"], unique=False)
    op.create_index("ix_security_audit_timestamp", "security_audit_events", ["timestamp"], unique=False)
    op.create_index("ix_security_audit_event_type", "security_audit_events", ["event_type"], unique=False)
    op.create_index("ix_security_audit_tool_name", "security_audit_events", ["tool_name"], unique=False)
    op.create_index(
        "ix_security_audit_user_timestamp", "security_audit_events", ["user_id", "timestamp"], unique=False
    )
    op.create_index(
        "ix_security_audit_user_event", "security_audit_events", ["user_id", "event_type"], unique=False
    )

    # 4. user_capabilities
    op.create_table(
        "user_capabilities",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("web_research", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("browser", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("voice", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("vision", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("computer_control", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("developer_tools", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("automation", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_capabilities")
    op.drop_table("security_audit_events")
    op.drop_table("security_approval_requests")
    op.drop_table("security_sessions")
