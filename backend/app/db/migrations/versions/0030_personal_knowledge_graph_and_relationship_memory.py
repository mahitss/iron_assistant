"""Migration for Personal Knowledge Graph and Relationship Memory Engine (Task 50).

Revision ID: 0030_personal_knowledge_graph_and_relationship_memory
Revises: 0029_social_and_communication_intelligence
Create Date: 2026-09-10 06:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_personal_knowledge_graph_and_relationship_memory"
down_revision: str | None = "0029_social_and_communication_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. kg_nodes
    op.create_table(
        "kg_nodes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False),
        sa.Column("canonical_name", sa.String(length=256), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, default="PRIVATE"),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, default=1.0),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_nodes_user_id", "kg_nodes", ["user_id"])
    op.create_index("ix_kg_nodes_project_id", "kg_nodes", ["project_id"])
    op.create_index("ix_kg_nodes_node_type", "kg_nodes", ["node_type"])
    op.create_index("ix_kg_nodes_canonical_name", "kg_nodes", ["canonical_name"])

    # 2. kg_edges
    op.create_table(
        "kg_edges",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("source_node_id", sa.String(length=64), nullable=False),
        sa.Column("relationship", sa.String(length=64), nullable=False),
        sa.Column("target_node_id", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, default=1.0),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(length=32), nullable=False, default="PRIVATE"),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_edges_source_node_id", "kg_edges", ["source_node_id"])
    op.create_index("ix_kg_edges_target_node_id", "kg_edges", ["target_node_id"])
    op.create_index("ix_kg_edges_relationship", "kg_edges", ["relationship"])
    op.create_index("ix_kg_edges_user_id", "kg_edges", ["user_id"])

    # 3. kg_assertions
    op.create_table(
        "kg_assertions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("predicate", sa.String(length=128), nullable=False),
        sa.Column("object", sa.Text(), nullable=False),
        sa.Column("source_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, default=1.0),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("scope", sa.String(length=32), nullable=False, default="PRIVATE"),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_assertions_subject", "kg_assertions", ["subject"])
    op.create_index("ix_kg_assertions_user_id", "kg_assertions", ["user_id"])

    # 4. kg_decisions
    op.create_table(
        "kg_decisions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("question", sa.String(length=512), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("alternatives_json", sa.JSON(), nullable=False),
        sa.Column("rationale_reference", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(length=128), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, default="PROJECT"),
        sa.Column("confidence", sa.Float(), nullable=False, default=1.0),
        sa.Column("status", sa.String(length=32), nullable=False, default="ACTIVE"),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_decisions_user_id", "kg_decisions", ["user_id"])
    op.create_index("ix_kg_decisions_project_id", "kg_decisions", ["project_id"])

    # 5. kg_preferences
    op.create_table(
        "kg_preferences",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, default="PRIVATE"),
        sa.Column("confidence", sa.Float(), nullable=False, default=1.0),
        sa.Column("source_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_confirmed", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_preferences_category", "kg_preferences", ["category"])
    op.create_index("ix_kg_preferences_user_id", "kg_preferences", ["user_id"])

    # 6. kg_outcomes
    op.create_table(
        "kg_outcomes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("related_goal_id", sa.String(length=64), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False, default=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_outcomes_goal_id", "kg_outcomes", ["related_goal_id"])
    op.create_index("ix_kg_outcomes_user_id", "kg_outcomes", ["user_id"])

    # 7. kg_contradictions
    op.create_table(
        "kg_contradictions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("conflicting_assertions_json", sa.JSON(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, default="DETECTED"),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kg_contradictions_user_id", "kg_contradictions", ["user_id"])


def downgrade() -> None:
    op.drop_table("kg_contradictions")
    op.drop_table("kg_outcomes")
    op.drop_table("kg_preferences")
    op.drop_table("kg_decisions")
    op.drop_table("kg_assertions")
    op.drop_table("kg_edges")
    op.drop_table("kg_nodes")
