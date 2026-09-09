"""Migration for Kairo Long-Term Experience, Preferences, Learning Candidates, and Feedback.

Revision ID: 0010_experience_and_learning
Revises: 0009_unified_event_bus
Create Date: 2026-09-09 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_experience_and_learning"
down_revision: str | None = "0009_unified_event_bus"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. experiences table
    op.create_table(
        "experiences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="PROJECT"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CANDIDATE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_experiences_user_status", "experiences", ["user_id", "status"])
    op.create_index("ix_experiences_project_type", "experiences", ["project_id", "type"])
    op.create_index("ix_experiences_user_scope", "experiences", ["user_id", "scope"])

    # 2. preferences table
    op.create_table(
        "preferences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="USER"),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="USER_EXPLICIT"),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="HIGH"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_preferences_user_scope_key", "preferences", ["user_id", "scope", "key"])
    op.create_index("ix_preferences_user_status", "preferences", ["user_id", "status"])

    # 3. learning_candidates table
    op.create_table(
        "learning_candidates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("experience_id", sa.String(length=64), nullable=True),
        sa.Column("source_event", sa.String(length=128), nullable=False),
        sa.Column("proposed_change", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="LOW"),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="GLOBAL"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PROPOSED"),
        sa.Column("reviewer_id", sa.String(length=64), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_candidates_status", "learning_candidates", ["status"])
    op.create_index("ix_candidates_source_event", "learning_candidates", ["source_event"])

    # 4. user_feedback table
    op.create_table(
        "user_feedback",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("message_id", sa.String(length=64), nullable=True),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("correction", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_user_created", "user_feedback", ["user_id", "created_at"])
    op.create_index("ix_feedback_type", "user_feedback", ["feedback_type"])


def downgrade() -> None:
    op.drop_table("user_feedback")
    op.drop_table("learning_candidates")
    op.drop_table("preferences")
    op.drop_table("experiences")
