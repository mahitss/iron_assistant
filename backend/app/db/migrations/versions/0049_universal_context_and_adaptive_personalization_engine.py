"""Universal context and adaptive personalization engine tables (Task 69).

Revision ID: 0049_universal_context_and_adaptive_personalization_engine
Revises: 0048_autonomous_knowledge_and_memory_consolidation_engine
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0049_universal_context_and_adaptive_personalization_engine"
down_revision: str | None = "0048_autonomous_knowledge_and_memory_consolidation_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Adaptive Preferences
    op.create_table(
        "adaptive_preferences",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("preference_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="INFERRED_PREFERENCE", nullable=False),
        sa.Column("confidence", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("occurrences", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_adaptive_preferences_pref_id", "adaptive_preferences", ["preference_id"])
    op.create_index("ix_adaptive_preferences_user_id", "adaptive_preferences", ["user_id"])
    op.create_index("ix_adaptive_preferences_tenant_id", "adaptive_preferences", ["tenant_id"])
    op.create_index("ix_adaptive_preferences_category", "adaptive_preferences", ["category"])

    # 2. Context Snapshots
    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("snapshot_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("goal_id", sa.String(length=64), nullable=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True),
        sa.Column("environment", sa.String(length=64), nullable=True),
        sa.Column("token_estimate", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quality_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("selected_items_json", sa.JSON(), nullable=False),
        sa.Column("retrieval_reasons_json", sa.JSON(), nullable=False),
        sa.Column("missing_context_json", sa.JSON(), nullable=False),
        sa.Column("conflicts_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_snapshots_snapshot_id", "context_snapshots", ["snapshot_id"])
    op.create_index("ix_context_snapshots_request_id", "context_snapshots", ["request_id"])
    op.create_index("ix_context_snapshots_tenant_id", "context_snapshots", ["tenant_id"])
    op.create_index("ix_context_snapshots_user_id", "context_snapshots", ["user_id"])

    # 3. Context Feedback Records
    op.create_table(
        "context_feedback_records",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("feedback_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("context_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("items_used", sa.JSON(), nullable=False),
        sa.Column("items_ignored", sa.JSON(), nullable=False),
        sa.Column("items_misleading", sa.JSON(), nullable=False),
        sa.Column("items_missing", sa.JSON(), nullable=False),
        sa.Column("retrieval_latency_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("task_outcome", sa.String(length=64), server_default="SUCCESS", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_context_feedback_feedback_id", "context_feedback_records", ["feedback_id"])
    op.create_index("ix_context_feedback_context_id", "context_feedback_records", ["context_id"])
    op.create_index("ix_context_feedback_tenant_id", "context_feedback_records", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("context_feedback_records")
    op.drop_table("context_snapshots")
    op.drop_table("adaptive_preferences")
