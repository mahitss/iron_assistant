"""Migration for Kairo Identity, Sessions, Device Trust, Presence, and Handoff (Task 33).

Revision ID: 0013_identity_sessions_and_device_trust
Revises: 0012_world_model_and_environment
Create Date: 2026-09-09 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_identity_sessions_and_device_trust"
down_revision: str | None = "0012_world_model_and_environment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. identity_sessions table
    op.create_table(
        "identity_sessions",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("client_type", sa.String(length=32), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_identity_sessions_user_id", "identity_sessions", ["user_id"])
    op.create_index("ix_identity_sessions_status", "identity_sessions", ["status"])
    op.create_index("ix_identity_sessions_user_status", "identity_sessions", ["user_id", "status"])
    op.create_index("ix_identity_sessions_device_id", "identity_sessions", ["device_id"])

    # 2. identity_presence table
    op.create_table(
        "identity_presence",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("interface", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_identity_presence_user_id", "identity_presence", ["user_id"])
    op.create_index("ix_identity_presence_session_id", "identity_presence", ["session_id"])
    op.create_index("ix_identity_presence_state", "identity_presence", ["state"])

    # 3. handoff_contexts table
    op.create_table(
        "handoff_contexts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_session_id", sa.String(length=64), nullable=False),
        sa.Column("target_session_id", sa.String(length=64), nullable=True),
        sa.Column("target_device_id", sa.String(length=64), nullable=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("relevant_context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_handoff_contexts_user_id", "handoff_contexts", ["user_id"])
    op.create_index("ix_handoff_contexts_token_hash", "handoff_contexts", ["token_hash"], unique=True)

    # 4. Extend devices table with explicit trust and pairing fields
    op.add_column(
        "devices",
        sa.Column("trust_status", sa.String(length=32), nullable=False, server_default="UNTRUSTED"),
    )
    op.add_column(
        "devices",
        sa.Column("client_type", sa.String(length=32), nullable=False, server_default="LOCAL_COMPANION"),
    )
    op.add_column(
        "devices",
        sa.Column("pairing_code_hash", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "devices",
        sa.Column("pairing_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "devices",
        sa.Column("trust_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "devices",
        sa.Column("capabilities", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.create_index("ix_devices_trust_status", "devices", ["trust_status"])


def downgrade() -> None:
    op.drop_index("ix_devices_trust_status", table_name="devices")
    op.drop_column("devices", "capabilities")
    op.drop_column("devices", "trust_expires_at")
    op.drop_column("devices", "pairing_expires_at")
    op.drop_column("devices", "pairing_code_hash")
    op.drop_column("devices", "client_type")
    op.drop_column("devices", "trust_status")

    op.drop_index("ix_handoff_contexts_token_hash", table_name="handoff_contexts")
    op.drop_index("ix_handoff_contexts_user_id", table_name="handoff_contexts")
    op.drop_table("handoff_contexts")

    op.drop_index("ix_identity_presence_state", table_name="identity_presence")
    op.drop_index("ix_identity_presence_session_id", table_name="identity_presence")
    op.drop_index("ix_identity_presence_user_id", table_name="identity_presence")
    op.drop_table("identity_presence")

    op.drop_index("ix_identity_sessions_device_id", table_name="identity_sessions")
    op.drop_index("ix_identity_sessions_user_status", table_name="identity_sessions")
    op.drop_index("ix_identity_sessions_status", table_name="identity_sessions")
    op.drop_index("ix_identity_sessions_user_id", table_name="identity_sessions")
    op.drop_table("identity_sessions")
