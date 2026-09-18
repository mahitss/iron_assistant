"""Autonomous Hypothesis Management, Competing Explanations, Evidence Update, Falsification & Uncertainty Resolution Engine tables (Task 115).

Revision ID: 0083_autonomous_hypothesis_management_and_competing_explanations
Revises: 0082_autonomous_active_observation_and_value_of_information
Create Date: 2026-09-18 11:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0083_autonomous_hypothesis_management_and_competing_explanations"
down_revision: str | None = "0082_autonomous_active_observation_and_value_of_information"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. hypothesis_sets_t115
    op.create_table(
        "hypothesis_sets_t115",
        sa.Column("set_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("target_description", sa.Text(), server_default="", nullable=False),
        sa.Column("target_incident_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("active_hypothesis_ids_json", sa.JSON(), nullable=False),
        sa.Column("rejected_hypothesis_ids_json", sa.JSON(), nullable=False),
        sa.Column("unknown_hypothesis_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("unresolved_conflicts_json", sa.JSON(), nullable=False),
        sa.Column("relationships_json", sa.JSON(), nullable=False),
        sa.Column("discriminators_json", sa.JSON(), nullable=False),
        sa.Column("information_gaps_json", sa.JSON(), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("resolution_summary", sa.String(length=128), server_default="CAUSE_UNKNOWN", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. hypotheses_t115
    op.create_table(
        "hypotheses_t115",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("set_id", sa.String(length=64), sa.ForeignKey("hypothesis_sets_t115.set_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("claim_json", sa.JSON(), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CANDIDATE", nullable=False, index=True),
        sa.Column("provenance", sa.String(length=32), server_default="GENERATED", nullable=False),
        sa.Column("proposer_agent_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("is_unknown_hypothesis", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("mechanism_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("causal_node_refs_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("falsification_conditions_json", sa.JSON(), nullable=False),
        sa.Column("confidence_profile_json", sa.JSON(), nullable=False),
        sa.Column("assessments_json", sa.JSON(), nullable=False),
        sa.Column("supporting_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("contradicting_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("falsifying_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("parent_hypothesis_ids_json", sa.JSON(), nullable=False),
        sa.Column("child_hypothesis_ids_json", sa.JSON(), nullable=False),
        sa.Column("superseded_by_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("staleness_reason", sa.String(length=256), nullable=True),
        sa.Column("contradiction_search_performed", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("bias_guard_triggers_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. hypothesis_evidence_t115
    op.create_table(
        "hypothesis_evidence_t115",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_type", sa.String(length=32), server_default="system", nullable=False),
        sa.Column("source_agent_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("independence", sa.String(length=32), server_default="INDEPENDENT", nullable=False, index=True),
        sa.Column("evidence_type", sa.String(length=32), server_default="OBSERVATION", nullable=False, index=True),
        sa.Column("direct_status", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("freshness_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("reliability_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("is_simulation", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_counterfactual", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("provenance", sa.Text(), server_default="", nullable=False),
        sa.Column("parent_evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=True),
        sa.Column("observation_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. hypothesis_predictions_t115
    op.create_table(
        "hypothesis_predictions_t115",
        sa.Column("prediction_id", sa.String(length=64), primary_key=True),
        sa.Column("hypothesis_id", sa.String(length=64), sa.ForeignKey("hypotheses_t115.hypothesis_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("predicted_event", sa.Text(), nullable=False),
        sa.Column("predicted_state_json", sa.JSON(), nullable=False),
        sa.Column("expected_metric", sa.String(length=128), nullable=True),
        sa.Column("expected_value_range_json", sa.JSON(), nullable=True),
        sa.Column("expected_timing_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("uncertainty_range", sa.Float(), server_default="0.1", nullable=False),
        sa.Column("source_model", sa.String(length=64), server_default="causal_model", nullable=False),
        sa.Column("observed_outcome_json", sa.JSON(), nullable=True),
        sa.Column("outcome_status", sa.String(length=32), server_default="PENDING", nullable=False, index=True),
        sa.Column("failure_notes", sa.Text(), nullable=True),
        sa.Column("validity_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validity_window_end", sa.DateTime(timezone=True), nullable=True),
    )

    # 5. hypothesis_snapshots_t115
    op.create_table(
        "hypothesis_snapshots_t115",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("set_id", sa.String(length=64), sa.ForeignKey("hypothesis_sets_t115.set_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("causal_model_version", sa.String(length=64), server_default="causal_v1", nullable=False),
        sa.Column("context_snapshot_id", sa.String(length=64), nullable=True),
        sa.Column("world_state_id", sa.String(length=64), nullable=True),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("hypotheses_state_json", sa.JSON(), nullable=False),
        sa.Column("evidence_state_json", sa.JSON(), nullable=False),
        sa.Column("relationships_state_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("hypothesis_snapshots_t115")
    op.drop_table("hypothesis_predictions_t115")
    op.drop_table("hypothesis_evidence_t115")
    op.drop_table("hypotheses_t115")
    op.drop_table("hypothesis_sets_t115")
