"""Migration for Multi-Agent Collaboration, Contracts, Disagreements, and Workspace Artifacts (Task 44).

Revision ID: 0024_multi_agent_collaboration
Revises: 0023_adaptive_learning
Create Date: 2026-09-09 23:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024_multi_agent_collaboration"
down_revision: str | None = "0023_adaptive_learning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. agent_contracts
    op.create_table(
        "agent_contracts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collaboration_id", sa.String(length=64), nullable=True),
        sa.Column("parent_goal", sa.Text(), nullable=False),
        sa.Column("assigned_objective", sa.Text(), nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("agent_role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("inputs_json", sa.JSON(), nullable=False),
        sa.Column("expected_outputs_json", sa.JSON(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("budget_json", sa.JSON(), nullable=False),
        sa.Column("success_criteria_json", sa.JSON(), nullable=False),
        sa.Column("verification_requirements_json", sa.JSON(), nullable=False),
        sa.Column("permissions_json", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_contracts_collab_id", "agent_contracts", ["collaboration_id"], unique=False)
    op.create_index("ix_agent_contracts_agent_id", "agent_contracts", ["agent_id"], unique=False)
    op.create_index("ix_agent_contracts_agent_role", "agent_contracts", ["agent_role"], unique=False)
    op.create_index("ix_agent_contracts_status", "agent_contracts", ["status"], unique=False)
    op.create_index("ix_agent_contracts_user_id", "agent_contracts", ["user_id"], unique=False)
    op.create_index("ix_agent_contracts_project_id", "agent_contracts", ["project_id"], unique=False)
    op.create_index("ix_agent_contracts_collab_agent", "agent_contracts", ["collaboration_id", "agent_id"], unique=False)
    op.create_index("ix_agent_contracts_user_status", "agent_contracts", ["user_id", "status"], unique=False)

    # 2. agent_collaborations
    op.create_table(
        "agent_collaborations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("supervisor_id", sa.String(length=64), nullable=False, server_default="supervisor_default"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PLANNING"),
        sa.Column("plan_dag_json", sa.JSON(), nullable=False),
        sa.Column("participants_json", sa.JSON(), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("synthesis_summary", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="UNVERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_collaborations_status", "agent_collaborations", ["status"], unique=False)
    op.create_index("ix_agent_collaborations_user_id", "agent_collaborations", ["user_id"], unique=False)
    op.create_index("ix_agent_collaborations_project_id", "agent_collaborations", ["project_id"], unique=False)
    op.create_index("ix_agent_collaborations_verif", "agent_collaborations", ["verification_status"], unique=False)
    op.create_index("ix_agent_collaborations_user_proj", "agent_collaborations", ["user_id", "project_id"], unique=False)
    op.create_index("ix_agent_collaborations_user_status", "agent_collaborations", ["user_id", "status"], unique=False)

    # 3. agent_messages
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collaboration_id", sa.String(length=64), nullable=False),
        sa.Column("contract_id", sa.String(length=64), nullable=True),
        sa.Column("sender_id", sa.String(length=64), nullable=False),
        sa.Column("recipient_id", sa.String(length=64), nullable=False),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="NORMAL"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_messages_collab_id", "agent_messages", ["collaboration_id"], unique=False)
    op.create_index("ix_agent_messages_contract_id", "agent_messages", ["contract_id"], unique=False)
    op.create_index("ix_agent_messages_sender_id", "agent_messages", ["sender_id"], unique=False)
    op.create_index("ix_agent_messages_recipient_id", "agent_messages", ["recipient_id"], unique=False)
    op.create_index("ix_agent_messages_type", "agent_messages", ["message_type"], unique=False)
    op.create_index("ix_agent_messages_collab_sender", "agent_messages", ["collaboration_id", "sender_id"], unique=False)
    op.create_index("ix_agent_messages_collab_recipient", "agent_messages", ["collaboration_id", "recipient_id"], unique=False)
    op.create_index("ix_agent_messages_created", "agent_messages", ["created_at"], unique=False)

    # 4. agent_disagreements
    op.create_table(
        "agent_disagreements",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collaboration_id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("participants_json", sa.JSON(), nullable=False),
        sa.Column("claims_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("resolution_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_disagreements_collab_id", "agent_disagreements", ["collaboration_id"], unique=False)
    op.create_index("ix_agent_disagreements_severity", "agent_disagreements", ["severity"], unique=False)
    op.create_index("ix_agent_disagreements_status", "agent_disagreements", ["status"], unique=False)

    # 5. agent_workspace_artifacts
    op.create_table(
        "agent_workspace_artifacts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("collaboration_id", sa.String(length=64), nullable=False),
        sa.Column("contract_id", sa.String(length=64), nullable=True),
        sa.Column("creator_agent_id", sa.String(length=64), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_artifacts_collab_id", "agent_workspace_artifacts", ["collaboration_id"], unique=False)
    op.create_index("ix_agent_artifacts_contract_id", "agent_workspace_artifacts", ["contract_id"], unique=False)
    op.create_index("ix_agent_artifacts_creator_id", "agent_workspace_artifacts", ["creator_agent_id"], unique=False)
    op.create_index("ix_agent_artifacts_type", "agent_workspace_artifacts", ["artifact_type"], unique=False)
    op.create_index("ix_agent_artifacts_hash", "agent_workspace_artifacts", ["content_hash"], unique=False)
    op.create_index("ix_agent_artifacts_collab_creator", "agent_workspace_artifacts", ["collaboration_id", "creator_agent_id"], unique=False)
    op.create_index("ix_agent_artifacts_collab_type", "agent_workspace_artifacts", ["collaboration_id", "artifact_type"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_workspace_artifacts")
    op.drop_table("agent_disagreements")
    op.drop_table("agent_messages")
    op.drop_table("agent_collaborations")
    op.drop_table("agent_contracts")
