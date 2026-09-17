"""Autonomous multi-agent collaboration, delegation, supervision and swarm orchestration engine tables (Task 96).

Revision ID: 0064_autonomous_multi_agent_collaboration_and_swarm_orchestration
Revises: 0063_autonomous_execution_governance_and_action_transactions
Create Date: 2026-09-17 01:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0064_autonomous_multi_agent_collaboration_and_swarm_orchestration"
down_revision: str | None = "0063_autonomous_execution_governance_and_action_transactions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. agent_identities
    op.create_table(
        "agent_identities",
        sa.Column("agent_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("parent_agent_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("capability_scope_json", sa.JSON(), nullable=False),
        sa.Column("context_scope", sa.String(length=64), server_default="PRIVATE_AGENT_CONTEXT", nullable=False),
        sa.Column("resource_scope_json", sa.JSON(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("lifecycle_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("trust_score", sa.Float(), server_default="0.85", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_identities_agent_id", "agent_identities", ["agent_id"])
    op.create_index("ix_agent_identities_session_id", "agent_identities", ["session_id"])
    op.create_index("ix_agent_identities_role", "agent_identities", ["role"])
    op.create_index("ix_agent_identities_parent_id", "agent_identities", ["parent_agent_id"])

    # 2. agent_orchestration_tasks
    op.create_table(
        "agent_orchestration_tasks",
        sa.Column("task_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("parent_task_id", sa.String(length=64), nullable=True),
        sa.Column("root_task_id", sa.String(length=64), nullable=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("role_needed", sa.String(length=32), nullable=False),
        sa.Column("assigned_agent_id", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.String(length=16), server_default="NORMAL", nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("dependency_state", sa.String(length=32), server_default="READY", nullable=False),
        sa.Column("required_capabilities_json", sa.JSON(), nullable=False),
        sa.Column("resource_budget_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_orch_tasks_task_id", "agent_orchestration_tasks", ["task_id"])
    op.create_index("ix_agent_orch_tasks_session_id", "agent_orchestration_tasks", ["session_id"])
    op.create_index("ix_agent_orch_tasks_parent_task_id", "agent_orchestration_tasks", ["parent_task_id"])
    op.create_index("ix_agent_orch_tasks_assigned_agent_id", "agent_orchestration_tasks", ["assigned_agent_id"])

    # 3. agent_messages
    op.create_table(
        "agent_messages",
        sa.Column("message_id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("sender_id", sa.String(length=64), nullable=False),
        sa.Column("recipient_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_messages_msg_id", "agent_messages", ["message_id"])
    op.create_index("ix_agent_messages_session_id", "agent_messages", ["session_id"])
    op.create_index("ix_agent_messages_sender_id", "agent_messages", ["sender_id"])
    op.create_index("ix_agent_messages_recipient_id", "agent_messages", ["recipient_id"])


def downgrade() -> None:
    op.drop_table("agent_messages")
    op.drop_table("agent_orchestration_tasks")
    op.drop_table("agent_identities")
