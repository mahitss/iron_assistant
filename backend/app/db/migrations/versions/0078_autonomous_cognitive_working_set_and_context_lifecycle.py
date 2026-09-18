"""Autonomous Cognitive Working Set, Relevance Packing & Context Lifecycle Engine tables (Task 110).

Revision ID: 0078_autonomous_cognitive_working_set_and_context_lifecycle
Revises: 0077_autonomous_attention_focus_and_interruption_governance
Create Date: 2026-09-18 05:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0078_autonomous_cognitive_working_set_and_context_lifecycle"
down_revision: str | None = "0077_autonomous_attention_focus_and_interruption_governance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. working_sets_t110
    op.create_table(
        "working_sets_t110",
        sa.Column("working_set_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False, index=True),
        sa.Column("user_scope", sa.String(length=64), server_default="default_user", nullable=False, index=True),
        sa.Column("operation_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("operation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("request_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("session_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("mission_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("goal_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("situation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("decision_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("action_transaction_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("agent_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("lifecycle", sa.String(length=32), server_default="DRAFT", nullable=False, index=True),
        sa.Column("quality_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("completeness_estimate", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("confidence_summary", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("compressed_item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("has_untrusted_content", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("sections_json", sa.JSON(), nullable=False),
        sa.Column("budget_json", sa.JSON(), nullable=False),
        sa.Column("conflicts_json", sa.JSON(), nullable=False),
        sa.Column("gaps_json", sa.JSON(), nullable=False),
        sa.Column("exclusions_json", sa.JSON(), nullable=False),
        sa.Column("pinned_items_json", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_ws_t110_tenant_user_op",
        "working_sets_t110",
        ["tenant_id", "user_scope", "operation_type"],
    )
    op.create_index(
        "ix_ws_t110_lifecycle_created",
        "working_sets_t110",
        ["lifecycle", "created_at"],
    )

    # 2. working_set_versions_t110
    op.create_table(
        "working_set_versions_t110",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("trigger_reason", sa.String(length=64), nullable=False),
        sa.Column("modified_sections_json", sa.JSON(), nullable=False),
        sa.Column("added_item_ids_json", sa.JSON(), nullable=False),
        sa.Column("removed_item_ids_json", sa.JSON(), nullable=False),
        sa.Column("quality_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_wsv_t110_ws_ver",
        "working_set_versions_t110",
        ["working_set_id", "version"],
        unique=True,
    )

    # 3. context_items_t110
    op.create_table(
        "context_items_t110",
        sa.Column("item_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("section", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_payload_json", sa.JSON(), nullable=False),
        sa.Column("inclusion", sa.String(length=32), server_default="OPTIONAL", nullable=False),
        sa.Column("relevance_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("relevance_components_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("freshness_classification", sa.String(length=32), server_default="FRESH", nullable=False),
        sa.Column("freshness_json", sa.JSON(), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("compression_level", sa.String(length=32), server_default="NONE", nullable=False),
        sa.Column("token_estimate", sa.Integer(), server_default="0", nullable=False),
        sa.Column("character_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_pinned", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_untrusted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_citem_t110_ws_section",
        "context_items_t110",
        ["working_set_id", "section"],
    )
    op.create_index(
        "ix_citem_t110_ws_score",
        "context_items_t110",
        ["working_set_id", "relevance_score"],
    )

    # 4. context_sections_t110
    op.create_table(
        "context_sections_t110",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("section_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.String(length=128), nullable=False),
        sa.Column("item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_empty", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_csec_t110_ws_type",
        "context_sections_t110",
        ["working_set_id", "section_type"],
        unique=True,
    )

    # 5. context_budgets_t110
    op.create_table(
        "context_budgets_t110",
        sa.Column("budget_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("max_tokens", sa.Integer(), server_default="8000", nullable=False),
        sa.Column("max_bytes", sa.Integer(), server_default="64000", nullable=False),
        sa.Column("max_items", sa.Integer(), server_default="60", nullable=False),
        sa.Column("max_retrieval_calls", sa.Integer(), server_default="20", nullable=False),
        sa.Column("latency_budget_ms", sa.Float(), server_default="250.0", nullable=False),
        sa.Column("used_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("used_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("used_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("retrieval_calls_made", sa.Integer(), server_default="0", nullable=False),
        sa.Column("actual_latency_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_exhausted", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("exhaustion_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. context_transformations_t110
    op.create_table(
        "context_transformations_t110",
        sa.Column("transformation_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("transformation_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("input_item_ids_json", sa.JSON(), nullable=False),
        sa.Column("output_item_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("information_loss", sa.String(length=32), server_default="NONE", nullable=False),
        sa.Column("is_reversible", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("original_size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("transformed_size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 7. context_dependencies_t110
    op.create_table(
        "context_dependencies_t110",
        sa.Column("dependency_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_item_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("target_item_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("relationship", sa.String(length=32), nullable=False, index=True),
        sa.Column("is_blocking", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. context_conflicts_t110
    op.create_table(
        "context_conflicts_t110",
        sa.Column("conflict_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("competing_item_ids_json", sa.JSON(), nullable=False),
        sa.Column("conflict_dimension", sa.String(length=64), nullable=False, index=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("resolution_status", sa.String(length=32), server_default="UNRESOLVED", nullable=False),
        sa.Column("arbitration_reference", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 9. context_gaps_t110
    op.create_table(
        "context_gaps_t110",
        sa.Column("gap_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("missing_information", sa.Text(), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("expected_source", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("is_blocking", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("confidence_impact", sa.Float(), server_default="0.2", nullable=False),
        sa.Column("suggested_retrieval", sa.Text(), nullable=True),
        sa.Column("estimated_retrieval_cost", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 10. context_leases_t110
    op.create_table(
        "context_leases_t110",
        sa.Column("lease_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("working_set_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("state", sa.String(length=32), server_default="VALID", nullable=False, index=True),
        sa.Column("ttl_seconds", sa.Float(), server_default="60.0", nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidation_reason", sa.String(length=128), nullable=True),
    )

    # 11. context_quality_assessments_t110
    op.create_table(
        "context_quality_assessments_t110",
        sa.Column("assessment_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("relevance_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("freshness_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("completeness_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("provenance_coverage_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("contradiction_visibility_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("redundancy_penalty", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("compression_quality_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("budget_efficiency_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("latency_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("source_diversity_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("task_alignment_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("safety_coverage_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("isolation_correctness_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("composite_quality", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 12. context_snapshots_t110
    op.create_table(
        "context_snapshots_t110",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("working_set_version", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("operation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("item_ids_json", sa.JSON(), nullable=False),
        sa.Column("source_versions_json", sa.JSON(), nullable=False),
        sa.Column("transformations_applied_json", sa.JSON(), nullable=False),
        sa.Column("freshness_summary_json", sa.JSON(), nullable=False),
        sa.Column("conflict_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("gap_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quality_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("has_untrusted_content", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 13. context_feedback_t110
    op.create_table(
        "context_feedback_t110",
        sa.Column("feedback_id", sa.String(length=64), primary_key=True),
        sa.Column("working_set_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("operation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("items_used_json", sa.JSON(), nullable=False),
        sa.Column("items_ignored_json", sa.JSON(), nullable=False),
        sa.Column("items_misleading_json", sa.JSON(), nullable=False),
        sa.Column("items_missing_json", sa.JSON(), nullable=False),
        sa.Column("was_compression_harmful", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("was_freshness_sufficient", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("context_size_rating", sa.String(length=32), server_default="OPTIMAL", nullable=False),
        sa.Column("downstream_outcome", sa.String(length=32), server_default="SUCCESS", nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("context_feedback_t110")
    op.drop_table("context_snapshots_t110")
    op.drop_table("context_quality_assessments_t110")
    op.drop_table("context_leases_t110")
    op.drop_table("context_gaps_t110")
    op.drop_table("context_conflicts_t110")
    op.drop_table("context_dependencies_t110")
    op.drop_table("context_transformations_t110")
    op.drop_table("context_budgets_t110")
    op.drop_table("context_sections_t110")
    op.drop_table("context_items_t110")
    op.drop_table("working_set_versions_t110")
    op.drop_table("working_sets_t110")
