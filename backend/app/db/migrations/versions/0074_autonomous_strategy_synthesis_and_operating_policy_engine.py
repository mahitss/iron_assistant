"""Autonomous Knowledge-to-Action Learning, Strategy Synthesis & Adaptive Operating Policy Engine tables (Task 106).

Revision ID: 0074_autonomous_strategy_synthesis_and_operating_policy_engine
Revises: 0073_autonomous_adaptation_and_governed_evolution_engine
Create Date: 2026-09-18 01:45:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0074_autonomous_strategy_synthesis_and_operating_policy_engine"
down_revision: str | None = "0073_autonomous_adaptation_and_governed_evolution_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. strategies
    op.create_table(
        "strategies",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("stable_id", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False, index=True),
        sa.Column("category", sa.String(length=64), nullable=False, index=True),
        sa.Column("objective", sa.Text(), server_default="", nullable=False),
        sa.Column("recommended_approach", sa.Text(), server_default="", nullable=False),
        sa.Column("current_version_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("lifecycle_status", sa.String(length=32), server_default="CANDIDATE", nullable=False, index=True),
        sa.Column("domain_scope", sa.String(length=128), server_default="SYSTEM", nullable=False, index=True),
        sa.Column("tested_domain", sa.Text(), server_default="", nullable=False),
        sa.Column("supported_domain", sa.Text(), server_default="", nullable=False),
        sa.Column("unknown_domain", sa.Text(), server_default="", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("success_rate", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("failure_rate", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validity_window_seconds", sa.Integer(), server_default="604800", nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False, index=True),
        sa.Column("is_safety_critical", sa.Boolean(), server_default=sa.text("false"), nullable=False, index=True),
        sa.Column("provenance_type", sa.String(length=64), server_default="EXPERIENCE_MINING", nullable=False),
        sa.Column("provenance_id", sa.String(length=128), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. strategy_versions
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("parent_version_id", sa.String(length=64), nullable=True),
        sa.Column("change_reason", sa.Text(), server_default="", nullable=False),
        sa.Column("change_description", sa.Text(), server_default="", nullable=False),
        sa.Column("parameters", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("rules", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), server_default="CANDIDATE", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("evidence_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("counterexample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. strategy_conditions
    op.create_table(
        "strategy_conditions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("condition_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("operator", sa.String(length=32), server_default="EQUALS", nullable=False),
        sa.Column("field_path", sa.String(length=255), nullable=False),
        sa.Column("target_value", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. strategy_preconditions
    op.create_table(
        "strategy_preconditions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("precondition_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("requirement_description", sa.Text(), server_default="", nullable=False),
        sa.Column("verification_key", sa.String(length=255), nullable=False),
        sa.Column("expected_state", sa.JSON(), server_default="true", nullable=False),
        sa.Column("is_hard_requirement", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. strategy_contraindications
    op.create_table(
        "strategy_contraindications",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("contraindication_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("severity", sa.String(length=32), server_default="PROHIBITIVE", nullable=False, index=True),
        sa.Column("trigger_condition", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. strategy_outcomes
    op.create_table(
        "strategy_outcomes",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("dimension", sa.String(length=64), nullable=False, index=True),
        sa.Column("expected_delta", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("variance", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("success_criteria", sa.Text(), server_default="", nullable=False),
        sa.Column("measurement_unit", sa.String(length=32), server_default="percentage", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. strategy_failure_modes
    op.create_table(
        "strategy_failure_modes",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("failure_class", sa.String(length=64), nullable=False, index=True),
        sa.Column("symptom", sa.Text(), server_default="", nullable=False),
        sa.Column("known_cause", sa.Text(), server_default="", nullable=False),
        sa.Column("frequency", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("mitigation_strategy_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. strategy_applicabilities
    op.create_table(
        "strategy_applicabilities",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True),
        sa.Column("evaluation_context", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("applicability_status", sa.String(length=32), server_default="UNCERTAIN", nullable=False, index=True),
        sa.Column("applicability_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("blocking_reasons", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("uncertainty_reasons", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. strategy_evidences
    op.create_table(
        "strategy_evidences",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_id", sa.String(length=128), nullable=False, index=True),
        sa.Column("is_counterexample", sa.Boolean(), server_default=sa.text("false"), nullable=False, index=True),
        sa.Column("claim", sa.Text(), server_default="", nullable=False),
        sa.Column("observed_metrics", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("environmental_context", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("capability_version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("confidence_weight", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sealed_hash_sha256", sa.String(length=64), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. strategy_evaluations
    op.create_table(
        "strategy_evaluations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True),
        sa.Column("evaluator", sa.String(length=128), server_default="benchmark", nullable=False),
        sa.Column("evaluation_type", sa.String(length=64), server_default="BENCHMARK", nullable=False),
        sa.Column("sample_size", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metrics", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("verdict", sa.String(length=32), server_default="INCONCLUSIVE", nullable=False, index=True),
        sa.Column("holdout_passed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("generalization_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("evaluation_evidence_ref", sa.String(length=128), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 11. strategy_usages
    op.create_table(
        "strategy_usages",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("mission_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("situation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("selected", sa.Boolean(), server_default=sa.text("false"), nullable=False, index=True),
        sa.Column("execution_context", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 12. strategy_feedbacks
    op.create_table(
        "strategy_feedbacks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True),
        sa.Column("usage_id", sa.String(length=64), nullable=True),
        sa.Column("decision_id", sa.String(length=64), nullable=True),
        sa.Column("action_id", sa.String(length=64), nullable=True),
        sa.Column("outcome_status", sa.String(length=32), server_default="SUCCESS", nullable=False, index=True),
        sa.Column("actual_metrics", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("expected_vs_actual_delta", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("observed_failure_mode", sa.String(length=64), nullable=True),
        sa.Column("resource_cost", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("user_intervention", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 13. strategy_conflicts
    op.create_table(
        "strategy_conflicts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("strategy_a_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("strategy_b_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("conflict_type", sa.String(length=32), server_default="DIRECT", nullable=False, index=True),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("detected_under_context", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("resolution_hint", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 14. strategy_supersessions
    op.create_table(
        "strategy_supersessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("superseded_strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("superseding_strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("superseded_version_id", sa.String(length=64), nullable=True),
        sa.Column("superseding_version_id", sa.String(length=64), nullable=True),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("evidence_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 15. strategy_proposals
    op.create_table(
        "strategy_proposals",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("proposal_title", sa.String(length=255), nullable=False, index=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("target_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("proposed_by", sa.String(length=128), server_default="experience_miner", nullable=False),
        sa.Column("rationale", sa.Text(), server_default="", nullable=False),
        sa.Column("mined_patterns_summary", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False, index=True),
        sa.Column("experiment_plan_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. strategy_reviews
    op.create_table(
        "strategy_reviews",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("proposal_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("reviewer", sa.String(length=128), server_default="kairo_governance", nullable=False),
        sa.Column("decision", sa.String(length=32), server_default="APPROVED", nullable=False, index=True),
        sa.Column("comments", sa.Text(), server_default="", nullable=False),
        sa.Column("governance_approval_id", sa.String(length=64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 17. strategy_events
    op.create_table(
        "strategy_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("strategy_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version_id", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("strategy_events")
    op.drop_table("strategy_reviews")
    op.drop_table("strategy_proposals")
    op.drop_table("strategy_supersessions")
    op.drop_table("strategy_conflicts")
    op.drop_table("strategy_feedbacks")
    op.drop_table("strategy_usages")
    op.drop_table("strategy_evaluations")
    op.drop_table("strategy_evidences")
    op.drop_table("strategy_applicabilities")
    op.drop_table("strategy_failure_modes")
    op.drop_table("strategy_outcomes")
    op.drop_table("strategy_contraindications")
    op.drop_table("strategy_preconditions")
    op.drop_table("strategy_conditions")
    op.drop_table("strategy_versions")
    op.drop_table("strategies")
