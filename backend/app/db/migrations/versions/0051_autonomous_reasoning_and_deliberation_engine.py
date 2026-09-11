"""Autonomous reasoning and deliberation engine tables (Task 71).

Revision ID: 0051_autonomous_reasoning_and_deliberation_engine
Revises: 0050_autonomous_attention_and_cognitive_resource_engine
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0051_autonomous_reasoning_and_deliberation_engine"
down_revision: str | None = "0050_autonomous_attention_and_cognitive_resource_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Reasoning Sessions
    op.create_table(
        "reasoning_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("workspace_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("user_id", sa.String(length=64), server_default="default_user", nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("goal_id", sa.String(length=64), nullable=True),
        sa.Column("mission_id", sa.String(length=64), nullable=True),
        sa.Column("attention_id", sa.String(length=64), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("intent", sa.String(length=128), server_default="", nullable=False),
        sa.Column("depth", sa.String(length=32), server_default="STANDARD", nullable=False),
        sa.Column("current_state", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("confidence", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("uncertainty_state", sa.String(length=32), server_default="UNCERTAIN", nullable=False),
        sa.Column("budget_json", sa.JSON(), nullable=False),
        sa.Column("explanation_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reasoning_sessions_reasoning_id", "reasoning_sessions", ["reasoning_id"])
    op.create_index("ix_reasoning_sessions_tenant_id", "reasoning_sessions", ["tenant_id"])
    op.create_index("ix_reasoning_sessions_current_state", "reasoning_sessions", ["current_state"])
    op.create_index("ix_rsn_sess_tenant_state", "reasoning_sessions", ["tenant_id", "current_state"])
    op.create_index("ix_rsn_sess_attention", "reasoning_sessions", ["tenant_id", "attention_id"])

    # 2. Reasoning Subproblems
    op.create_table(
        "reasoning_subproblems",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("subproblem_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.String(length=64), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("priority", sa.String(length=32), server_default="NORMAL", nullable=False),
        sa.Column("depth_level", sa.Integer(), server_default="1", nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("required_evidence_json", sa.JSON(), nullable=False),
        sa.Column("hypotheses_json", sa.JSON(), nullable=False),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reasoning_subproblems_subproblem_id", "reasoning_subproblems", ["subproblem_id"])
    op.create_index("ix_reasoning_subproblems_reasoning_id", "reasoning_subproblems", ["reasoning_id"])
    op.create_index("ix_reasoning_subproblems_tenant_id", "reasoning_subproblems", ["tenant_id"])

    # 3. Reasoning Hypotheses
    op.create_table(
        "reasoning_hypotheses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False),
        sa.Column("subproblem_id", sa.String(length=64), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CANDIDATE", nullable=False),
        sa.Column("confidence", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="internal", nullable=False),
        sa.Column("supporting_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("contradicting_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("falsification_conditions_json", sa.JSON(), nullable=False),
        sa.Column("counterarguments_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reasoning_hypotheses_hypothesis_id", "reasoning_hypotheses", ["hypothesis_id"])
    op.create_index("ix_reasoning_hypotheses_reasoning_id", "reasoning_hypotheses", ["reasoning_id"])
    op.create_index("ix_reasoning_hypotheses_tenant_id", "reasoning_hypotheses", ["tenant_id"])

    # 4. Reasoning Evidence Items
    op.create_table(
        "reasoning_evidence_items",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("source_type", sa.String(length=64), server_default="observation", nullable=False),
        sa.Column("source_id", sa.String(length=64), nullable=False),
        sa.Column("content_summary", sa.Text(), nullable=False),
        sa.Column("trust_level", sa.String(length=32), server_default="KNOWN_SOURCE", nullable=False),
        sa.Column("reliability", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("relevance", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("independence_group", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("verification_state", sa.String(length=32), server_default="UNVERIFIED", nullable=False),
        sa.Column("is_conflict", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("raw_data_json", sa.JSON(), nullable=False),
        sa.Column("conflicting_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reasoning_evidence_items_evidence_id", "reasoning_evidence_items", ["evidence_id"])
    op.create_index("ix_reasoning_evidence_items_reasoning_id", "reasoning_evidence_items", ["reasoning_id"])
    op.create_index("ix_reasoning_evidence_items_tenant_id", "reasoning_evidence_items", ["tenant_id"])

    # 5. Reasoning Assumptions
    op.create_table(
        "reasoning_assumptions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assumption_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="UNVERIFIED", nullable=False),
        sa.Column("validation_source", sa.String(length=128), nullable=True),
        sa.Column("dependent_conclusion_ids_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reasoning_assumptions_assumption_id", "reasoning_assumptions", ["assumption_id"])
    op.create_index("ix_reasoning_assumptions_reasoning_id", "reasoning_assumptions", ["reasoning_id"])
    op.create_index("ix_reasoning_assumptions_tenant_id", "reasoning_assumptions", ["tenant_id"])

    # 6. Reasoning Conclusions
    op.create_table(
        "reasoning_conclusions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conclusion_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False),
        sa.Column("subproblem_id", sa.String(length=64), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PROVISIONAL", nullable=False),
        sa.Column("confidence", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("uncertainty_state", sa.String(length=32), server_default="KNOWN", nullable=False),
        sa.Column("falsification_tested", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("verification_id", sa.String(length=64), nullable=True),
        sa.Column("supporting_hypothesis_ids_json", sa.JSON(), nullable=False),
        sa.Column("assumption_ids_json", sa.JSON(), nullable=False),
        sa.Column("counterarguments_addressed_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reasoning_conclusions_conclusion_id", "reasoning_conclusions", ["conclusion_id"])
    op.create_index("ix_reasoning_conclusions_reasoning_id", "reasoning_conclusions", ["reasoning_id"])
    op.create_index("ix_reasoning_conclusions_tenant_id", "reasoning_conclusions", ["tenant_id"])

    # 7. Reasoning Graphs
    op.create_table(
        "reasoning_graphs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("graph_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("nodes_json", sa.JSON(), nullable=False),
        sa.Column("edges_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reasoning_graphs_graph_id", "reasoning_graphs", ["graph_id"])
    op.create_index("ix_reasoning_graphs_reasoning_id", "reasoning_graphs", ["reasoning_id"])
    op.create_index("ix_reasoning_graphs_tenant_id", "reasoning_graphs", ["tenant_id"])

    # 8. Reasoning Traces
    op.create_table(
        "reasoning_traces",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("reasoning_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("events_json", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reasoning_traces_trace_id", "reasoning_traces", ["trace_id"])
    op.create_index("ix_reasoning_traces_reasoning_id", "reasoning_traces", ["reasoning_id"])
    op.create_index("ix_reasoning_traces_tenant_id", "reasoning_traces", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("reasoning_traces")
    op.drop_table("reasoning_graphs")
    op.drop_table("reasoning_conclusions")
    op.drop_table("reasoning_assumptions")
    op.drop_table("reasoning_evidence_items")
    op.drop_table("reasoning_hypotheses")
    op.drop_table("reasoning_subproblems")
    op.drop_table("reasoning_sessions")
