"""Migration for Causal Reasoning & Causal Graph Engine (Task 55).

Revision ID: 0035_causal_reasoning_and_causal_graph
Revises: 0034_environmental_intelligence_and_digital_twin
Create Date: 2026-09-15 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_causal_reasoning_and_causal_graph"
down_revision: str | None = "0034_environmental_intelligence_and_digital_twin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. causal_graphs
    op.create_table(
        "causal_graphs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("graph_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="SYSTEM"),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nodes", sa.JSON(), nullable=False),
        sa.Column("edges", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("graph_id"),
    )
    op.create_index("ix_causal_graphs_scope", "causal_graphs", ["scope", "scope_id"])
    op.create_index("ix_causal_graphs_timestamp", "causal_graphs", ["timestamp"])

    # 2. causal_nodes
    op.create_table(
        "causal_nodes",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=False),
        sa.Column("variable", sa.String(length=128), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id"),
    )
    op.create_index("ix_causal_nodes_entity_var", "causal_nodes", ["entity", "variable"])
    op.create_index("ix_causal_nodes_timestamp", "causal_nodes", ["timestamp"])

    # 3. causal_edges
    op.create_table(
        "causal_edges",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("edge_id", sa.String(length=128), nullable=False),
        sa.Column("cause", sa.String(length=128), nullable=False),
        sa.Column("effect", sa.String(length=128), nullable=False),
        sa.Column("relationship", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(length=64), nullable=False, server_default="SYSTEM"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="CANDIDATE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edge_id"),
    )
    op.create_index("ix_causal_edges_cause_effect", "causal_edges", ["cause", "effect"])
    op.create_index("ix_causal_edges_rel_status", "causal_edges", ["relationship", "status"])

    # 4. causal_hypotheses
    op.create_table(
        "causal_hypotheses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False),
        sa.Column("cause", sa.String(length=128), nullable=False),
        sa.Column("effect", sa.String(length=128), nullable=False),
        sa.Column("mechanism", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="PROPOSED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hypothesis_id"),
    )
    op.create_index("ix_causal_hypo_cause_effect", "causal_hypotheses", ["cause", "effect"])
    op.create_index("ix_causal_hypo_status", "causal_hypotheses", ["status"])

    # 5. causal_evidence
    op.create_table(
        "causal_evidence",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("observation", sa.JSON(), nullable=False),
        sa.Column("strength", sa.String(length=64), nullable=False, server_default="MODERATE"),
        sa.Column("independence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id"),
    )
    op.create_index("ix_causal_evidence_type", "causal_evidence", ["type"])
    op.create_index("ix_causal_evidence_timestamp", "causal_evidence", ["timestamp"])

    # 6. root_cause_analyses
    op.create_table(
        "root_cause_analyses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("analysis_id", sa.String(length=64), nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("candidate_causes", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("eliminated_causes", sa.JSON(), nullable=False),
        sa.Column("surviving_causes", sa.JSON(), nullable=False),
        sa.Column("root_cause", sa.String(length=256), nullable=True),
        sa.Column("contributing_factors", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="INVESTIGATING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_id"),
    )
    op.create_index("ix_rca_incident", "root_cause_analyses", ["incident_id"])
    op.create_index("ix_rca_status", "root_cause_analyses", ["status"])

    # 7. causal_interventions
    op.create_table(
        "causal_interventions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("intervention_id", sa.String(length=64), nullable=False),
        sa.Column("target", sa.String(length=128), nullable=False),
        sa.Column("change", sa.JSON(), nullable=False),
        sa.Column("expected_effect", sa.JSON(), nullable=False),
        sa.Column("actual_effect", sa.JSON(), nullable=True),
        sa.Column("authorization", sa.JSON(), nullable=False),
        sa.Column("risk", sa.String(length=64), nullable=False, server_default="MEDIUM"),
        sa.Column("verification_plan", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="PROPOSED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intervention_id"),
    )
    op.create_index("ix_causal_interventions_target", "causal_interventions", ["target"])
    op.create_index("ix_causal_interventions_status", "causal_interventions", ["status"])

    # 8. counterfactual_scenarios
    op.create_table(
        "counterfactual_scenarios",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("baseline", sa.JSON(), nullable=False),
        sa.Column("intervention", sa.JSON(), nullable=False),
        sa.Column("expected_difference", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("is_hypothetical", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="GENERATED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id"),
    )
    op.create_index("ix_counterfactual_status", "counterfactual_scenarios", ["status"])

    # 9. causal_experiments
    op.create_table(
        "causal_experiments",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("experiment_id", sa.String(length=64), nullable=False),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False),
        sa.Column("treatment", sa.JSON(), nullable=False),
        sa.Column("control", sa.JSON(), nullable=False),
        sa.Column("metric", sa.String(length=128), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("authorization", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id"),
    )
    op.create_index("ix_causal_exp_hypo", "causal_experiments", ["hypothesis_id"])
    op.create_index("ix_causal_exp_status", "causal_experiments", ["status"])


def downgrade() -> None:
    op.drop_table("causal_experiments")
    op.drop_table("counterfactual_scenarios")
    op.drop_table("causal_interventions")
    op.drop_table("root_cause_analyses")
    op.drop_table("causal_evidence")
    op.drop_table("causal_hypotheses")
    op.drop_table("causal_edges")
    op.drop_table("causal_nodes")
    op.drop_table("causal_graphs")
