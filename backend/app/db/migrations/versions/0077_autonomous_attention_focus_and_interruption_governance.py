"""Autonomous Attention, Cognitive Resource Allocation, Focus Management & Interruption Governance Engine tables (Task 109).

Revision ID: 0077_autonomous_attention_focus_and_interruption_governance
Revises: 0076_autonomous_intent_understanding_and_goal_inference
Create Date: 2026-09-18 04:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0077_autonomous_attention_focus_and_interruption_governance"
down_revision: str | None = "0076_autonomous_intent_understanding_and_goal_inference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. attention_candidates_t109
    op.create_table(
        "attention_candidates_t109",
        sa.Column("candidate_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False, index=True),
        sa.Column("source", sa.String(length=64), nullable=False, index=True),
        sa.Column("type", sa.String(length=64), nullable=False, index=True),
        sa.Column("target", sa.String(length=128), server_default="unspecified", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False),
        sa.Column("lifecycle", sa.String(length=32), server_default="CREATED", nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("related_mission", sa.String(length=64), nullable=True, index=True),
        sa.Column("related_situation", sa.String(length=64), nullable=True, index=True),
        sa.Column("related_goal", sa.String(length=64), nullable=True, index=True),
        sa.Column("related_decision", sa.String(length=64), nullable=True, index=True),
        sa.Column("related_action", sa.String(length=64), nullable=True),
        sa.Column("related_capability", sa.String(length=64), nullable=True),
        sa.Column("related_user_intent", sa.String(length=64), nullable=True, index=True),
        sa.Column("salience_composite", sa.Float(), server_default="0.5", nullable=False, index=True),
        sa.Column("uncertainty", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("freshness", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("age_seconds", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("deferral_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("aging_boost", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_adversarial_dampened", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("score_details_json", sa.JSON(), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_attn_t109_tenant_type_score",
        "attention_candidates_t109",
        ["tenant_id", "type", "salience_composite"],
    )
    op.create_index(
        "ix_attn_t109_tenant_lifecycle",
        "attention_candidates_t109",
        ["tenant_id", "lifecycle"],
    )

    # 2. attention_evidence
    op.create_table(
        "attention_evidence",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_uri", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=64), server_default="INTERNAL_SIGNAL", nullable=False),
        sa.Column("is_trusted", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("credibility", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("claim", sa.Text(), server_default="", nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. focus_sessions
    op.create_table(
        "focus_sessions",
        sa.Column("session_id", sa.String(length=64), primary_key=True),
        sa.Column("parent_session_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("depth", sa.Integer(), server_default="0", nullable=False),
        sa.Column("primary_target_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(length=64), server_default="USER_REQUEST", nullable=False),
        sa.Column("expected_duration_sec", sa.Integer(), server_default="300", nullable=False),
        sa.Column("resource_budget_json", sa.JSON(), nullable=False),
        sa.Column("interruption_policy", sa.String(length=32), server_default="NORMAL", nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("success_condition", sa.Text(), server_default="Objective accomplished", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("resumption_context_json", sa.JSON(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. focus_transitions
    op.create_table(
        "focus_transitions",
        sa.Column("transition_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("previous_target", sa.String(length=128), nullable=True),
        sa.Column("new_target", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("trigger_candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("switching_cost", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.85", nullable=False),
        sa.Column("details", sa.Text(), server_default="", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 5. interruption_decisions
    op.create_table(
        "interruption_decisions",
        sa.Column("decision_id", sa.String(length=64), primary_key=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("incoming_candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("classification", sa.String(length=32), nullable=False),
        sa.Column("should_interrupt", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("cost_breakdown_json", sa.JSON(), nullable=False),
        sa.Column("reason", sa.Text(), server_default="", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. attention_budgets
    op.create_table(
        "attention_budgets",
        sa.Column("budget_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("active_reasoning_pct", sa.Float(), server_default="100.0", nullable=False),
        sa.Column("background_pct", sa.Float(), server_default="30.0", nullable=False),
        sa.Column("pending_queue_slots", sa.Integer(), server_default="50", nullable=False),
        sa.Column("reserved_emergency_pct", sa.Float(), server_default="20.0", nullable=False),
        sa.Column("consumed_budget_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("context_tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("context_token_capacity", sa.Integer(), server_default="128000", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 7. attention_allocations
    op.create_table(
        "attention_allocations",
        sa.Column("allocation_id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("estimated_reasoning_cost", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("expected_benefit", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("urgency", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("resource_class", sa.String(length=64), server_default="STANDARD_REASONING", nullable=False),
        sa.Column("economy_status", sa.String(length=32), server_default="REQUESTED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. attention_suppressions
    op.create_table(
        "attention_suppressions",
        sa.Column("suppression_id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("fingerprint", sa.String(length=128), nullable=False, index=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("suppressed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 9. attention_watches
    op.create_table(
        "attention_watches",
        sa.Column("watch_id", sa.String(length=64), primary_key=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("condition_type", sa.String(length=64), nullable=False),
        sa.Column("condition_expr", sa.Text(), nullable=False),
        sa.Column("reconsideration_trigger", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 10. attention_snapshots_t109
    op.create_table(
        "attention_snapshots_t109",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("health_status", sa.String(length=64), server_default="HEALTHY", nullable=False),
        sa.Column("active_focus_session_json", sa.JSON(), nullable=False),
        sa.Column("nested_stack_json", sa.JSON(), nullable=False),
        sa.Column("queue_summary_json", sa.JSON(), nullable=False),
        sa.Column("budget_summary_json", sa.JSON(), nullable=False),
        sa.Column("active_missions_json", sa.JSON(), nullable=False),
        sa.Column("active_intents_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 11. attention_events_t109
    op.create_table(
        "attention_events_t109",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("candidate_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("attention_events_t109")
    op.drop_table("attention_snapshots_t109")
    op.drop_table("attention_watches")
    op.drop_table("attention_suppressions")
    op.drop_table("attention_allocations")
    op.drop_table("attention_budgets")
    op.drop_table("interruption_decisions")
    op.drop_table("focus_transitions")
    op.drop_table("focus_sessions")
    op.drop_table("attention_evidence")
    op.drop_table("attention_candidates_t109")
