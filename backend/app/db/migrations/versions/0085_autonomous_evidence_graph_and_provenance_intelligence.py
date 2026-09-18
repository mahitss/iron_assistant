"""Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine tables (Task 117).

Revision ID: 0085_autonomous_evidence_graph_and_provenance_intelligence
Revises: 0084_autonomous_claim_verification_and_provenance_engine
Create Date: 2026-09-18 16:00:00.000000
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0085_autonomous_evidence_graph_and_provenance_intelligence"
down_revision: str | None = "0084_autonomous_claim_verification_and_provenance_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. evidence_graph_nodes_t117
    op.create_table(
        "evidence_graph_nodes_t117",
        sa.Column("node_id", sa.String(length=64), primary_key=True),
        sa.Column("node_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("source_system", sa.String(length=64), server_default="generic", nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("temporal_scope_json", sa.JSON(), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=32), server_default="ACTIVE", nullable=False, index=True),
        sa.Column("provenance_status", sa.String(length=32), server_default="UNVERIFIED", nullable=False, index=True),
        sa.Column("freshness_state", sa.String(length=32), server_default="FRESH", nullable=False, index=True),
        sa.Column("integrity_state", sa.String(length=32), server_default="INTACT", nullable=False, index=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), server_default="", nullable=False, index=True),
    )

    # 2. evidence_graph_edges_t117
    op.create_table(
        "evidence_graph_edges_t117",
        sa.Column("edge_id", sa.String(length=64), primary_key=True),
        sa.Column("source_node_id", sa.String(length=64), sa.ForeignKey("evidence_graph_nodes_t117.node_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("target_node_id", sa.String(length=64), sa.ForeignKey("evidence_graph_nodes_t117.node_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("relationship_type", sa.String(length=32), nullable=False, index=True),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_system", sa.String(length=64), server_default="generic", nullable=False),
        sa.Column("actor_component", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("evidence_references_json", sa.JSON(), nullable=False),
        sa.Column("derivation_method", sa.String(length=64), server_default="DIRECT", nullable=False),
        sa.Column("verification_status", sa.String(length=32), server_default="UNVERIFIED", nullable=False),
        sa.Column("supersession_json", sa.JSON(), nullable=True),
        sa.Column("correction_json", sa.JSON(), nullable=True),
        sa.Column("scope_json", sa.JSON(), nullable=False),
    )

    # 3. evidence_graph_node_versions_t117
    op.create_table(
        "evidence_graph_node_versions_t117",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("node_id", sa.String(length=64), sa.ForeignKey("evidence_graph_nodes_t117.node_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("node_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_version", sa.Integer(), nullable=True),
    )

    # 4. evidence_graph_edge_versions_t117
    op.create_table(
        "evidence_graph_edge_versions_t117",
        sa.Column("version_id", sa.String(length=64), primary_key=True),
        sa.Column("edge_id", sa.String(length=64), sa.ForeignKey("evidence_graph_edges_t117.edge_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 5. evidence_graph_snapshots_t117
    op.create_table(
        "evidence_graph_snapshots_t117",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("graph_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("node_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("edge_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("query_scope_json", sa.JSON(), nullable=False),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("checksum", sa.String(length=64), server_default="", nullable=False, index=True),
        sa.Column("creation_reason", sa.String(length=256), server_default="AUDIT_SNAPSHOT", nullable=False),
        sa.Column("snapshot_data_json", sa.JSON(), nullable=False),
    )

    # 6. dependency_impacts_t117
    op.create_table(
        "dependency_impacts_t117",
        sa.Column("impact_id", sa.String(length=64), primary_key=True),
        sa.Column("target_node_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("target_node_type", sa.String(length=32), nullable=False),
        sa.Column("root_cause_node_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("cause_reason", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="DIRECT", nullable=False),
        sa.Column("impact_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. revalidation_candidates_t117
    op.create_table(
        "revalidation_candidates_t117",
        sa.Column("candidate_id", sa.String(length=64), primary_key=True),
        sa.Column("affected_node_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("affected_node_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("upstream_cause_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("severity", sa.String(length=32), server_default="DIRECT", nullable=False),
        sa.Column("freshness_state", sa.String(length=32), server_default="STALE", nullable=False),
        sa.Column("decision_impact", sa.String(length=256), nullable=True),
        sa.Column("mission_impact", sa.String(length=256), nullable=True),
        sa.Column("resource_estimate", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("expected_information_value", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("required_capability", sa.String(length=64), server_default="general_verification", nullable=False),
        sa.Column("recommended_next_step", sa.String(length=32), server_default="REVALIDATE_NOW", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. provenance_gaps_t117
    op.create_table(
        "provenance_gaps_t117",
        sa.Column("gap_id", sa.String(length=64), primary_key=True),
        sa.Column("affected_node_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("missing_relationship", sa.String(length=64), nullable=False),
        sa.Column("expected_node_type", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="POSSIBLE", nullable=False),
        sa.Column("recoverable", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("acquisition_method", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 9. evidence_fragility_t117
    op.create_table(
        "evidence_fragility_t117",
        sa.Column("assessment_id", sa.String(length=64), primary_key=True),
        sa.Column("node_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_concentration_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("provenance_completeness_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("freshness_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("reproducibility_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("dependency_depth", sa.Integer(), server_default="1", nullable=False),
        sa.Column("contradiction_exposure_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("single_source_dependence", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("transformation_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("unresolved_gaps_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("overall_fragility_label", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("dimension_findings_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 10. evidence_graph_events_t117
    op.create_table(
        "evidence_graph_events_t117",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False, index=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("causation_id", sa.String(length=64), nullable=True),
        sa.Column("actor_component", sa.String(length=64), server_default="evidence_graph", nullable=False),
        sa.Column("object_id", sa.String(length=64), nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evidence_graph_events_t117")
    op.drop_table("evidence_fragility_t117")
    op.drop_table("provenance_gaps_t117")
    op.drop_table("revalidation_candidates_t117")
    op.drop_table("dependency_impacts_t117")
    op.drop_table("evidence_graph_snapshots_t117")
    op.drop_table("evidence_graph_edge_versions_t117")
    op.drop_table("evidence_graph_node_versions_t117")
    op.drop_table("evidence_graph_edges_t117")
    op.drop_table("evidence_graph_nodes_t117")
