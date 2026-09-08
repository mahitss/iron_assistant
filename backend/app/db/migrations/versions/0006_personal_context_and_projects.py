"""Migration for Personal Context Engine, Projects, and resource associations.

Revision ID: 0006_personal_context
Revises: 0005_multi_agent
Create Date: 2026-09-09 01:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_personal_context"
down_revision: str | None = "0005_multi_agent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. projects
    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_user_id", "projects", ["user_id"], unique=False)
    op.create_index("ix_projects_name", "projects", ["name"], unique=False)
    op.create_index("ix_projects_status", "projects", ["status"], unique=False)
    op.create_index("ix_projects_last_active_at", "projects", ["last_active_at"], unique=False)
    op.create_index("ix_projects_user_status", "projects", ["user_id", "status"], unique=False)
    op.create_index("ix_projects_user_name", "projects", ["user_id", "name"], unique=False)

    # 2. project_repositories
    op.create_table(
        "project_repositories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("repository_path", sa.String(length=512), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_repositories_project_id", "project_repositories", ["project_id"], unique=False)
    op.create_index("ix_project_repo_path", "project_repositories", ["project_id", "repository_path"], unique=False)

    # 3. project_workflows
    op.create_table(
        "project_workflows",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_workflows_project_id", "project_workflows", ["project_id"], unique=False)
    op.create_index("ix_project_workflows_workflow_id", "project_workflows", ["workflow_id"], unique=False)

    # 4. project_conversations
    op.create_table(
        "project_conversations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_conversations_project_id", "project_conversations", ["project_id"], unique=False)
    op.create_index("ix_project_conversations_conversation_id", "project_conversations", ["conversation_id"], unique=False)

    # 5. user_context_settings
    op.create_table(
        "user_context_settings",
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("context_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("memory_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("project_context_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("proactive_context_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_context_settings")

    op.drop_index("ix_project_conversations_conversation_id", table_name="project_conversations")
    op.drop_index("ix_project_conversations_project_id", table_name="project_conversations")
    op.drop_table("project_conversations")

    op.drop_index("ix_project_workflows_workflow_id", table_name="project_workflows")
    op.drop_index("ix_project_workflows_project_id", table_name="project_workflows")
    op.drop_table("project_workflows")

    op.drop_index("ix_project_repo_path", table_name="project_repositories")
    op.drop_index("ix_project_repositories_project_id", table_name="project_repositories")
    op.drop_table("project_repositories")

    op.drop_index("ix_projects_user_name", table_name="projects")
    op.drop_index("ix_projects_user_status", table_name="projects")
    op.drop_index("ix_projects_last_active_at", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_index("ix_projects_user_id", table_name="projects")
    op.drop_table("projects")
