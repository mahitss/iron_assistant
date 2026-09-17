"""Autonomous Intent Understanding, Goal Inference, User Alignment & Request Semantics Engine tables (Task 108).

Revision ID: 0076_autonomous_intent_understanding_and_goal_inference
Revises: 0075_autonomous_belief_arbitration_and_world_model_revision
Create Date: 2026-09-18 03:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0076_autonomous_intent_understanding_and_goal_inference"
down_revision: str | None = "0075_autonomous_belief_arbitration_and_world_model_revision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. user_requests
    op.create_table(
        "user_requests",
        sa.Column("request_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("message_id", sa.String(length=64), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("cleaned_text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), server_default="en", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="DIRECT_USER", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="DEFAULT", nullable=False),
        sa.Column("context_reference_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="RECEIVED", nullable=False, index=True),
        sa.Column("is_external_content", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_requests_user_created", "user_requests", ["user_id", "created_at"])

    # 2. request_versions
    op.create_table(
        "request_versions",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("request_id", sa.String(length=64), sa.ForeignKey("user_requests.request_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("change_reason", sa.String(length=128), server_default="INITIAL", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. autonomous_intents
    op.create_table(
        "autonomous_intents",
        sa.Column("intent_id", sa.String(length=64), primary_key=True),
        sa.Column("request_id", sa.String(length=64), sa.ForeignKey("user_requests.request_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_intent_id", sa.String(length=64), nullable=True),
        sa.Column("dependency_ids_json", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, index=True),
        sa.Column("action_class", sa.String(length=64), nullable=True),
        sa.Column("target", sa.String(length=256), server_default="UNKNOWN", nullable=False),
        sa.Column("target_epistemic", sa.String(length=32), server_default="EXPLICIT", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="DEFAULT", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("user_visible_outcome", sa.Text(), server_default="", nullable=False),
        sa.Column("non_goals_json", sa.JSON(), nullable=False),
        sa.Column("external_effect", sa.String(length=32), server_default="INTERNAL_ONLY", nullable=False),
        sa.Column("priority", sa.String(length=32), server_default="NORMAL", nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deadline_epistemic", sa.String(length=32), server_default="UNKNOWN", nullable=False),
        sa.Column("target_confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("goal_confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("constraint_confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("deadline_confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("scope_confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("overall_confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="UNDERSTOOD", nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("is_superseded", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("superseded_by", sa.String(length=64), nullable=True),
        sa.Column("is_cancelled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. intent_candidates
    op.create_table(
        "intent_candidates",
        sa.Column("candidate_id", sa.String(length=64), primary_key=True),
        sa.Column("request_id", sa.String(length=64), sa.ForeignKey("user_requests.request_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("evidence_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. intent_versions
    op.create_table(
        "intent_versions",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("intent_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("reason_for_change", sa.String(length=128), server_default="INITIAL", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 6. goal_hypotheses
    op.create_table(
        "goal_hypotheses",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("target_state_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("epistemic_status", sa.String(length=32), server_default="INFERRED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. desired_outcomes
    op.create_table(
        "desired_outcomes",
        sa.Column("outcome_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("observable_outcome", sa.Text(), nullable=False),
        sa.Column("acceptance_criteria_json", sa.JSON(), nullable=False),
        sa.Column("quality_threshold", sa.String(length=128), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.String(length=64), server_default="DEFAULT", nullable=False),
        sa.Column("epistemic_status", sa.String(length=32), server_default="INFERRED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. intent_constraints
    op.create_table(
        "intent_constraints",
        sa.Column("constraint_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("constraint_type", sa.String(length=32), nullable=False),
        sa.Column("epistemic_strength", sa.String(length=32), server_default="EXPLICIT", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parameter", sa.String(length=128), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="USER_INSTRUCTION", nullable=False),
        sa.Column("is_hard_constraint", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. intent_preferences
    op.create_table(
        "intent_preferences",
        sa.Column("preference_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("is_current_request", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="EXPLICIT_USER", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. intent_requirements
    op.create_table(
        "intent_requirements",
        sa.Column("requirement_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("raw_statement", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("interpretation", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), server_default="USER_INSTRUCTION", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 11. intent_assumptions_v2
    op.create_table(
        "intent_assumptions_v2",
        sa.Column("assumption_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("assumption_type", sa.String(length=32), server_default="SAFE_DEFAULT", nullable=False),
        sa.Column("source", sa.String(length=64), server_default="SYSTEM_DEFAULT", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.85", nullable=False),
        sa.Column("impact_level", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("is_reversible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 12. intent_ambiguities_v2
    op.create_table(
        "intent_ambiguities_v2",
        sa.Column("ambiguity_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ambiguity_type", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=256), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("candidates_json", sa.JSON(), nullable=False),
        sa.Column("consequence_level", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("requires_user_clarification", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("resolution_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 13. intent_clarifications_v2
    op.create_table(
        "intent_clarifications_v2",
        sa.Column("clarification_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("ambiguity_id", sa.String(length=64), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("affected_decision", sa.String(length=256), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("safe_default", sa.String(length=256), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("user_response", sa.Text(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 14. intent_evidence_items
    op.create_table(
        "intent_evidence_items",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_ref", sa.String(length=256), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reliability", sa.Float(), server_default="0.9", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 15. intent_conflicts
    op.create_table(
        "intent_conflicts",
        sa.Column("conflict_id", sa.String(length=64), primary_key=True),
        sa.Column("primary_intent_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("conflicting_intent_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("conflict_type", sa.String(length=64), server_default="DIRECT_CONTRADICTION", nullable=False),
        sa.Column("is_resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. intent_resolutions
    op.create_table(
        "intent_resolutions",
        sa.Column("resolution_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("resolution_mechanism", sa.String(length=64), nullable=False),
        sa.Column("resolved_value_json", sa.JSON(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 17. intent_corrections
    op.create_table(
        "intent_corrections",
        sa.Column("correction_id", sa.String(length=64), primary_key=True),
        sa.Column("request_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("prior_intent_id", sa.String(length=64), nullable=False),
        sa.Column("revised_intent_id", sa.String(length=64), nullable=False),
        sa.Column("user_feedback_text", sa.Text(), nullable=False),
        sa.Column("scope_affected", sa.String(length=64), server_default="CURRENT_PROJECT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 18. intent_feedback_items
    op.create_table(
        "intent_feedback_items",
        sa.Column("feedback_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), sa.ForeignKey("autonomous_intents.intent_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("was_accurate", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("user_satisfaction_score", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 19. intent_snapshots
    op.create_table(
        "intent_snapshots",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("intent_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("request_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("intent_data_json", sa.JSON(), nullable=False),
        sa.Column("goal_hypotheses_json", sa.JSON(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("non_goals_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("external_effect", sa.String(length=32), server_default="INTERNAL_ONLY", nullable=False),
        sa.Column("confidence_breakdown_json", sa.JSON(), nullable=False),
    )

    # 20. intent_events
    op.create_table(
        "intent_events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("intent_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("request_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("user_id", sa.String(length=64), server_default="default_user", nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("intent_events")
    op.drop_table("intent_snapshots")
    op.drop_table("intent_feedback_items")
    op.drop_table("intent_corrections")
    op.drop_table("intent_resolutions")
    op.drop_table("intent_conflicts")
    op.drop_table("intent_evidence_items")
    op.drop_table("intent_clarifications_v2")
    op.drop_table("intent_ambiguities_v2")
    op.drop_table("intent_assumptions_v2")
    op.drop_table("intent_requirements")
    op.drop_table("intent_preferences")
    op.drop_table("intent_constraints")
    op.drop_table("desired_outcomes")
    op.drop_table("goal_hypotheses")
    op.drop_table("intent_versions")
    op.drop_table("intent_candidates")
    op.drop_table("autonomous_intents")
    op.drop_table("request_versions")
    op.drop_index("ix_user_requests_user_created", table_name="user_requests")
    op.drop_table("user_requests")
