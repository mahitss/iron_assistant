"""Autonomous Causal Explanation, Event Chain Reconstruction & Root-Cause Analysis Engine tables (Task 112).

Revision ID: 0080_autonomous_causal_explanation_and_root_cause_engine
Revises: 0079_autonomous_temporal_intelligence_and_event_history
Create Date: 2026-09-18 10:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0080_autonomous_causal_explanation_and_root_cause_engine"
down_revision: str | None = "0079_autonomous_temporal_intelligence_and_event_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. causal_explanations_t112
    op.create_table(
        "causal_explanations_t112",
        sa.Column("explanation_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("target_entity", sa.String(length=128), nullable=False, index=True),
        sa.Column("target_event_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("target_state_change", sa.String(length=128), nullable=True),
        sa.Column("lifecycle_stage", sa.String(length=32), server_default="REQUESTED", nullable=False, index=True),
        sa.Column("what_happened", sa.Text(), server_default="", nullable=False),
        sa.Column("what_changed", sa.Text(), server_default="", nullable=False),
        sa.Column("what_preceded_it", sa.Text(), server_default="", nullable=False),
        sa.Column("why_it_happened", sa.Text(), server_default="CAUSE UNKNOWN", nullable=False),
        sa.Column("contributing_factors_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("what_would_verify_this", sa.Text(), server_default="", nullable=False),
        sa.Column("root_cause_category", sa.String(length=64), server_default="UNKNOWN", nullable=False, index=True),
        sa.Column("primary_cause", sa.String(length=256), nullable=True),
        sa.Column("primary_mechanism", sa.Text(), nullable=True),
        sa.Column("causal_links_json", sa.JSON(), nullable=False),
        sa.Column("contributors_json", sa.JSON(), nullable=False),
        sa.Column("event_chain_json", sa.JSON(), nullable=False),
        sa.Column("alternatives_json", sa.JSON(), nullable=False),
        sa.Column("counterfactuals_json", sa.JSON(), nullable=False),
        sa.Column("unresolved_gaps_json", sa.JSON(), nullable=False),
        sa.Column("confidence_json", sa.JSON(), nullable=False),
        sa.Column("quality_json", sa.JSON(), nullable=False),
        sa.Column("composite_confidence", sa.Float(), server_default="0.5", nullable=False, index=True),
        sa.Column("is_verified", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_cause_unknown", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("superseded_by", sa.String(length=64), nullable=True),
        sa.Column("scope", sa.String(length=64), server_default="DEFAULT", nullable=False, index=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_expl_target_stage",
        "causal_explanations_t112",
        ["target_entity", "lifecycle_stage"],
    )

    # 2. causal_hypotheses_t112
    op.create_table(
        "causal_hypotheses_t112",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("explanation_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("hypothesis_summary", sa.Text(), nullable=False),
        sa.Column("proposed_cause", sa.String(length=256), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="POSSIBLE", nullable=False, index=True),
        sa.Column("supporting_points_json", sa.JSON(), nullable=False),
        sa.Column("contradicting_points_json", sa.JSON(), nullable=False),
        sa.Column("missing_evidence_json", sa.JSON(), nullable=False),
        sa.Column("discriminating_observation", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. causal_links_t112
    op.create_table(
        "causal_links_t112",
        sa.Column("link_id", sa.String(length=64), primary_key=True),
        sa.Column("explanation_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_node", sa.String(length=128), nullable=False, index=True),
        sa.Column("target_node", sa.String(length=128), nullable=False, index=True),
        sa.Column("relationship_role", sa.String(length=64), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="CANDIDATE", nullable=False, index=True),
        sa.Column("mechanism", sa.Text(), server_default="", nullable=False),
        sa.Column("lag_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_temporally_valid", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("confidence_json", sa.JSON(), nullable=False),
        sa.Column("supporting_evidence_json", sa.JSON(), nullable=False),
        sa.Column("contradicting_evidence_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_clink_source_target",
        "causal_links_t112",
        ["source_node", "target_node"],
    )

    # 4. explanation_verifications_t112
    op.create_table(
        "explanation_verifications_t112",
        sa.Column("verification_id", sa.String(length=64), primary_key=True),
        sa.Column("explanation_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("tested_hypothesis", sa.Text(), nullable=False),
        sa.Column("predicted_consequence", sa.Text(), nullable=False),
        sa.Column("actual_observation", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(length=32), server_default="UNRESOLVED", nullable=False, index=True),
        sa.Column("observation_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_by_actor", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("explanation_verifications_t112")
    op.drop_table("causal_links_t112")
    op.drop_table("causal_hypotheses_t112")
    op.drop_table("causal_explanations_t112")
