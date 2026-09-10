"""Collective intelligence and swarm reasoning engine tables (Task 64).

Revision ID: 0044_collective_intelligence_and_swarm_reasoning
Revises: 0043_knowledge_synthesis_and_research_intelligence
Create Date: 2026-09-11 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0044_collective_intelligence_and_swarm_reasoning"
down_revision: str | None = "0043_knowledge_synthesis_and_research_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Swarm Sessions Table
    op.create_table(
        "swarm_sessions",
        sa.Column("swarm_id", sa.String(length=64), primary_key=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("topology", sa.String(length=32), nullable=False, server_default="STAR"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="INITIALIZING"),
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
        sa.Column("consensus_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_swarm_sessions_swarm_id", "swarm_sessions", ["swarm_id"])
    op.create_index("ix_swarm_sessions_tenant_id", "swarm_sessions", ["tenant_id"])

    # 2. Swarm Tasks Table
    op.create_table(
        "swarm_tasks",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("swarm_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("role_needed", sa.String(length=64), nullable=False),
        sa.Column("assigned_agent_id", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("is_critical_path", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("result_id", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_swarm_tasks_task_id", "swarm_tasks", ["task_id"])
    op.create_index("ix_swarm_tasks_swarm_id", "swarm_tasks", ["swarm_id"])

    # 3. Swarm Results Table
    op.create_table(
        "swarm_results",
        sa.Column("result_id", sa.String(length=64), primary_key=True),
        sa.Column("swarm_id", sa.String(length=64), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_swarm_results_result_id", "swarm_results", ["result_id"])
    op.create_index("ix_swarm_results_swarm_id", "swarm_results", ["swarm_id"])
    op.create_index("ix_swarm_results_agent_id", "swarm_results", ["agent_id"])

    # 4. Swarm Disagreements Table
    op.create_table(
        "swarm_disagreements",
        sa.Column("disagreement_id", sa.String(length=64), primary_key=True),
        sa.Column("swarm_id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DETECTED"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_swarm_disagreements_disagreement_id", "swarm_disagreements", ["disagreement_id"])
    op.create_index("ix_swarm_disagreements_swarm_id", "swarm_disagreements", ["swarm_id"])

    # 5. Swarm Minority Reports Table
    op.create_table(
        "swarm_minority_reports",
        sa.Column("minority_id", sa.String(length=64), primary_key=True),
        sa.Column("swarm_id", sa.String(length=64), nullable=False),
        sa.Column("dissenting_agent_id", sa.String(length=64), nullable=False),
        sa.Column("dissenting_role", sa.String(length=64), nullable=False),
        sa.Column("position", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.75"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_swarm_minority_reports_minority_id", "swarm_minority_reports", ["minority_id"])
    op.create_index("ix_swarm_minority_reports_swarm_id", "swarm_minority_reports", ["swarm_id"])

    # 6. Swarm Audit Records Table
    op.create_table(
        "swarm_audit_records",
        sa.Column("sequence_number", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entry_hash", sa.String(length=128), nullable=False),
        sa.Column("previous_hash", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False, server_default="swarm_engine"),
        sa.Column("swarm_id", sa.String(length=64), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("details", sa.Text(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_swarm_audit_records_entry_hash", "swarm_audit_records", ["entry_hash"])
    op.create_index("ix_swarm_audit_records_swarm_id", "swarm_audit_records", ["swarm_id"])


def downgrade() -> None:
    op.drop_table("swarm_audit_records")
    op.drop_table("swarm_minority_reports")
    op.drop_table("swarm_disagreements")
    op.drop_table("swarm_results")
    op.drop_table("swarm_tasks")
    op.drop_table("swarm_sessions")
