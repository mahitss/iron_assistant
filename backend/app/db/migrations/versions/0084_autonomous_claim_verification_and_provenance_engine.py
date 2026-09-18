"""Autonomous Claim Verification, Source Integrity & Evidence Provenance Engine tables (Task 116).

Revision ID: 0084_autonomous_claim_verification_and_provenance_engine
Revises: 0083_autonomous_hypothesis_management_and_competing_explanations
Create Date: 2026-09-18 12:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0084_autonomous_claim_verification_and_provenance_engine"
down_revision: str | None = "0083_autonomous_hypothesis_management_and_competing_explanations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. verification_cases_t116
    op.create_table(
        "verification_cases_t116",
        sa.Column("case_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("claim_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="REQUESTED", nullable=False, index=True),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("assumptions_json", sa.JSON(), nullable=False),
        sa.Column("falsification_conditions_json", sa.JSON(), nullable=False),
        sa.Column("verification_requirements_json", sa.JSON(), nullable=False),
        sa.Column("resolution_summary", sa.Text(), server_default="", nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True, unique=True, index=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("superseded_by_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. claims_t116
    op.create_table(
        "claims_t116",
        sa.Column("claim_id", sa.String(length=64), primary_key=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=32), server_default="ATOMIC", nullable=False, index=True),
        sa.Column("subject", sa.String(length=128), server_default="", nullable=False),
        sa.Column("predicate", sa.String(length=128), server_default="", nullable=False),
        sa.Column("object_val", sa.Text(), server_default="", nullable=False),
        sa.Column("qualifiers_json", sa.JSON(), nullable=False),
        sa.Column("temporal_scope_json", sa.JSON(), nullable=False),
        sa.Column("spatial_scope_json", sa.JSON(), nullable=False),
        sa.Column("entity_scope_json", sa.JSON(), nullable=False),
        sa.Column("source_scope_json", sa.JSON(), nullable=False),
        sa.Column("falsification_conditions_json", sa.JSON(), nullable=False),
        sa.Column("expected_evidence_types_json", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("uncertainty", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("provenance_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 3. claim_fragments_t116
    op.create_table(
        "claim_fragments_t116",
        sa.Column("fragment_id", sa.String(length=64), primary_key=True),
        sa.Column("claim_id", sa.String(length=64), sa.ForeignKey("claims_t116.claim_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("fragment_type", sa.String(length=32), server_default="ATOMIC", nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(length=128), server_default="", nullable=False),
        sa.Column("predicate", sa.String(length=128), server_default="", nullable=False),
        sa.Column("object_val", sa.Text(), server_default="", nullable=False),
        sa.Column("dependencies_json", sa.JSON(), nullable=False),
        sa.Column("order_idx", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 4. sources_t116
    op.create_table(
        "sources_t116",
        sa.Column("source_id", sa.String(length=64), primary_key=True),
        sa.Column("uri", sa.String(length=512), nullable=False, index=True),
        sa.Column("category", sa.String(length=32), server_default="UNKNOWN", nullable=False, index=True),
        sa.Column("publisher", sa.String(length=256), server_default="", nullable=False),
        sa.Column("owner", sa.String(length=256), server_default="", nullable=False),
        sa.Column("auth_state", sa.String(length=32), server_default="UNAUTHENTICATED", nullable=False),
        sa.Column("trust_profile_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. source_snapshots_t116
    op.create_table(
        "source_snapshots_t116",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources_t116.source_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("headers_json", sa.JSON(), nullable=False),
        sa.Column("content_metadata_json", sa.JSON(), nullable=False),
        sa.Column("content_preview", sa.Text(), server_default="", nullable=False),
        sa.Column("parser_version", sa.String(length=64), server_default="default_v1", nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 6. source_relationships_t116
    op.create_table(
        "source_relationships_t116",
        sa.Column("relationship_id", sa.String(length=64), primary_key=True),
        sa.Column("source_a_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_b_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("relationship_type", sa.String(length=32), server_default="INDEPENDENT", nullable=False, index=True),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("justification", sa.Text(), server_default="", nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. evidence_artifacts_t116
    op.create_table(
        "evidence_artifacts_t116",
        sa.Column("evidence_id", sa.String(length=64), primary_key=True),
        sa.Column("source_id", sa.String(length=64), sa.ForeignKey("sources_t116.source_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("snapshot_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("location", sa.String(length=512), server_default="", nullable=False),
        sa.Column("offset_range", sa.String(length=128), server_default="", nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False, index=True),
        sa.Column("content_text", sa.Text(), server_default="", nullable=False),
        sa.Column("quality_profile_json", sa.JSON(), nullable=False),
        sa.Column("direct_status", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_simulated", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("is_counterfactual", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("parent_artifact_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. evidence_transformations_t116
    op.create_table(
        "evidence_transformations_t116",
        sa.Column("transformation_id", sa.String(length=64), primary_key=True),
        sa.Column("input_artifact_ids_json", sa.JSON(), nullable=False),
        sa.Column("output_artifact_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("component", sa.String(length=128), nullable=False),
        sa.Column("config_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("is_deterministic", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("input_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("output_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. provenance_links_t116
    op.create_table(
        "provenance_links_t116",
        sa.Column("link_id", sa.String(length=64), primary_key=True),
        sa.Column("from_entity_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("from_entity_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("to_entity_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("to_entity_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("predicate", sa.String(length=32), server_default="DERIVED_FROM", nullable=False, index=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. corroboration_groups_t116
    op.create_table(
        "corroboration_groups_t116",
        sa.Column("group_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("corroboration_type", sa.String(length=32), server_default="INDEPENDENT_SUPPORT", nullable=False, index=True),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("source_ids_json", sa.JSON(), nullable=False),
        sa.Column("temporal_alignment", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("semantic_alignment", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("scope_alignment", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("independence_assessment_json", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 11. contradiction_records_t116
    op.create_table(
        "contradiction_records_t116",
        sa.Column("contradiction_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("contradiction_type", sa.String(length=32), server_default="DIRECT_CONTRADICTION", nullable=False, index=True),
        sa.Column("claim_a_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("claim_b_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("evidence_a_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("evidence_b_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 12. reproduction_attempts_t116
    op.create_table(
        "reproduction_attempts_t116",
        sa.Column("attempt_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="NOT_ATTEMPTED", nullable=False, index=True),
        sa.Column("environment_fingerprint", sa.String(length=64), server_default="", nullable=False),
        sa.Column("input_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("output_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("deterministic", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), server_default="", nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 13. verification_results_t116
    op.create_table(
        "verification_results_t116",
        sa.Column("result_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("claim_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("status", sa.String(length=32), server_default="UNKNOWN", nullable=False, index=True),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("justification", sa.Text(), server_default="", nullable=False),
        sa.Column("evidence_ids_json", sa.JSON(), nullable=False),
        sa.Column("contradiction_ids_json", sa.JSON(), nullable=False),
        sa.Column("method_types_json", sa.JSON(), nullable=False),
        sa.Column("uncertainty_profile_json", sa.JSON(), nullable=False),
        sa.Column("gaps_json", sa.JSON(), nullable=False),
        sa.Column("reproducibility_status", sa.String(length=32), server_default="NOT_ATTEMPTED", nullable=False),
        sa.Column("validity_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validity_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 14. verification_gaps_t116
    op.create_table(
        "verification_gaps_t116",
        sa.Column("gap_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("missing_evidence_desc", sa.Text(), nullable=False),
        sa.Column("impact_reason", sa.Text(), nullable=False),
        sa.Column("affected_claim_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("possible_methods_json", sa.JSON(), nullable=False),
        sa.Column("expected_info_gain", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("cost", sa.Float(), server_default="0.1", nullable=False),
        sa.Column("risk", sa.Float(), server_default="0.1", nullable=False),
        sa.Column("urgency", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 15. verification_snapshots_t116
    op.create_table(
        "verification_snapshots_t116",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("snapshot_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("case_state_json", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 16. verification_events_t116
    op.create_table(
        "verification_events_t116",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("case_id", sa.String(length=64), sa.ForeignKey("verification_cases_t116.case_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("actor", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("causation_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("verification_events_t116")
    op.drop_table("verification_snapshots_t116")
    op.drop_table("verification_gaps_t116")
    op.drop_table("verification_results_t116")
    op.drop_table("reproduction_attempts_t116")
    op.drop_table("contradiction_records_t116")
    op.drop_table("corroboration_groups_t116")
    op.drop_table("provenance_links_t116")
    op.drop_table("evidence_transformations_t116")
    op.drop_table("evidence_artifacts_t116")
    op.drop_table("source_relationships_t116")
    op.drop_table("source_snapshots_t116")
    op.drop_table("sources_t116")
    op.drop_table("claim_fragments_t116")
    op.drop_table("claims_t116")
    op.drop_table("verification_cases_t116")
