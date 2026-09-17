"""Autonomous Cognitive Memory, Experience Consolidation & Lifelong Learning Fabric (Task 103).

Revision ID: 0071_autonomous_cognitive_memory_and_lifelong_learning_fabric
Revises: 0070_autonomous_cognitive_control_plane_and_unified_loop
Create Date: 2026-09-18 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0071_autonomous_cognitive_memory_and_lifelong_learning_fabric"
down_revision: str | None = "0070_autonomous_cognitive_control_plane_and_unified_loop"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. cognitive_experiences table
    op.create_table(
        "cognitive_experiences",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("experience_id", sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column("source_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("scope", sa.String(length=32), server_default="PROJECT", nullable=False, index=True),
        sa.Column("actor", sa.String(length=64), server_default="kairo_system", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("structured_facts", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("outcome", sa.String(length=32), server_default="SUCCESS", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("trust_classification", sa.String(length=64), server_default="OBSERVED", nullable=False, index=True),
        sa.Column("importance", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("recurrence_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("related_entities", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("related_missions", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("related_situations", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("related_decisions", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("related_actions", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("verification_references", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("world_state_references", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. cognitive_memories table
    op.create_table(
        "cognitive_memories",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("memory_id", sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column("memory_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("lifecycle_state", sa.String(length=32), server_default="ACTIVE", nullable=False, index=True),
        sa.Column("scope", sa.String(length=32), server_default="PROJECT", nullable=False, index=True),
        sa.Column("scope_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_data", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("importance", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("freshness", sa.String(length=32), server_default="CURRENT", nullable=False, index=True),
        sa.Column("trust_classification", sa.String(length=64), server_default="OBSERVED", nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("superseded_by", sa.String(length=64), nullable=True),
        sa.Column("supersedes", sa.String(length=64), nullable=True),
        sa.Column("source_experience_ids", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("related_entities", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("preconditions", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("procedure_steps", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("verification_criteria", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("exceptions", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("access_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("application_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("useful_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. cognitive_memory_conflicts table
    op.create_table(
        "cognitive_memory_conflicts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conflict_id", sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column("memory_a_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("memory_b_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("memory_a_claim", sa.Text(), nullable=False),
        sa.Column("memory_b_claim", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="PROJECT", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False, index=True),
        sa.Column("evidence", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. cognitive_memory_patterns table
    op.create_table(
        "cognitive_memory_patterns",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("pattern_id", sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column("pattern_type", sa.String(length=64), server_default="PATTERN", nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="PROJECT", nullable=False),
        sa.Column("recurrence_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("source_experience_ids", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("exceptions", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. cognitive_memory_feedbacks table
    op.create_table(
        "cognitive_memory_feedbacks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("feedback_id", sa.String(length=64), unique=True, nullable=False, index=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("application_id", sa.String(length=64), nullable=True),
        sa.Column("was_useful", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("caused_error", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("error_type", sa.String(length=64), nullable=True),
        sa.Column("empirical_outcome", sa.String(length=64), server_default="SUCCESS", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cognitive_memory_feedbacks")
    op.drop_table("cognitive_memory_patterns")
    op.drop_table("cognitive_memory_conflicts")
    op.drop_table("cognitive_memories")
    op.drop_table("cognitive_experiences")
