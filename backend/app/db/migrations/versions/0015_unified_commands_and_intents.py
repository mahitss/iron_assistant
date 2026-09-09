"""Migration for Kairo Unified Command, Intent, Reference Resolution, and Natural-Language Control Layer (Task 35).

Revision ID: 0015_unified_commands_and_intents
Revises: 0014_unified_notifications
Create Date: 2026-09-09 22:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_unified_commands_and_intents"
down_revision: str | None = "0014_unified_notifications"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. unified_commands table
    op.create_table(
        "unified_commands",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("attachments_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("source_interface", sa.String(length=32), nullable=False, server_default="WEB"),
        sa.Column("project_hint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_unified_commands_user_id", "unified_commands", ["user_id"])
    op.create_index("ix_unified_commands_session_id", "unified_commands", ["session_id"])
    op.create_index("ix_unified_commands_conversation_id", "unified_commands", ["conversation_id"])
    op.create_index("ix_unified_commands_user_created", "unified_commands", ["user_id", "created_at"])

    # 2. unified_intents table
    op.create_table(
        "unified_intents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("command_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("entities_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("references_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("target_json", sa.JSON(), nullable=True),
        sa.Column("constraints_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("requested_action", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("ambiguity_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("risk", sa.String(length=32), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="READY"),
        sa.Column("next_action", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["command_id"], ["unified_commands.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_unified_intents_command_id", "unified_intents", ["command_id"])
    op.create_index("ix_unified_intents_user_id", "unified_intents", ["user_id"])
    op.create_index("ix_unified_intents_user_type", "unified_intents", ["user_id", "type"])
    op.create_index("ix_unified_intents_user_created", "unified_intents", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_table("unified_intents")
    op.drop_table("unified_commands")
