"""Autonomous knowledge and memory consolidation engine tables (Task 68).

Revision ID: 0048_autonomous_knowledge_and_memory_consolidation_engine
Revises: 0047_metacognitive_control_and_self_audit_engine
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0048_autonomous_knowledge_and_memory_consolidation_engine"
down_revision: str | None = "0047_metacognitive_control_and_self_audit_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Durable Memories
    op.create_table(
        "durable_memories",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("user_id", sa.String(length=64), server_default="default_user", nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=True),
        sa.Column("cognitive_type", sa.String(length=32), server_default="MEMORY", nullable=False),
        sa.Column("memory_type", sa.String(length=32), server_default="EPISODIC_MEMORY", nullable=False),
        sa.Column("abstraction_level", sa.String(length=32), server_default="RAW_OBSERVATION", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("structured_payload", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("importance", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("relevance", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("freshness", sa.String(length=32), server_default="FRESH", nullable=False),
        sa.Column("sensitivity", sa.String(length=32), server_default="STANDARD", nullable=False),
        sa.Column("trust_level", sa.String(length=32), server_default="UNVERIFIED", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("superseded_by", sa.String(length=64), nullable=True),
        sa.Column("supersedes", sa.String(length=64), nullable=True),
        sa.Column("retention_policy", sa.String(length=64), server_default="DEFAULT", nullable=False),
        sa.Column("access_policy", sa.String(length=64), server_default="PROJECT_SCOPED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_consolidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=64), server_default="kairo_ingestion", nullable=False),
        sa.Column("updated_by", sa.String(length=64), server_default="kairo_ingestion", nullable=False),
    )
    op.create_index("ix_durable_memories_memory_id", "durable_memories", ["memory_id"])
    op.create_index("ix_durable_memories_tenant_id", "durable_memories", ["tenant_id"])
    op.create_index("ix_durable_memories_user_id", "durable_memories", ["user_id"])
    op.create_index("ix_durable_memories_project_id", "durable_memories", ["project_id"])
    op.create_index("ix_durable_memories_cog_type", "durable_memories", ["cognitive_type"])
    op.create_index("ix_durable_memories_mem_type", "durable_memories", ["memory_type"])
    op.create_index("ix_durable_memories_status", "durable_memories", ["status"])
    op.create_index("ix_durable_memories_freshness", "durable_memories", ["freshness"])
    op.create_index("ix_durable_memories_trust", "durable_memories", ["trust_level"])
    op.create_index("ix_durable_memories_expires_at", "durable_memories", ["expires_at"])
    op.create_index("ix_durable_memories_last_accessed", "durable_memories", ["last_accessed_at"])
    op.create_index(
        "ix_durable_mem_tenant_type_status",
        "durable_memories",
        ["tenant_id", "memory_type", "status"],
    )

    # 2. Memory Provenances
    op.create_table(
        "memory_provenances",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("provenance_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        sa.Column("source_type", sa.String(length=64), server_default="direct_observation", nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=True),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("event_refs", sa.JSON(), nullable=False),
        sa.Column("parent_memory_ids", sa.JSON(), nullable=False),
        sa.Column("derived_from_ids", sa.JSON(), nullable=False),
        sa.Column("related_memory_ids", sa.JSON(), nullable=False),
        sa.Column("decision_refs", sa.JSON(), nullable=False),
        sa.Column("goal_refs", sa.JSON(), nullable=False),
        sa.Column("plan_refs", sa.JSON(), nullable=False),
        sa.Column("incident_refs", sa.JSON(), nullable=False),
        sa.Column("prediction_refs", sa.JSON(), nullable=False),
        sa.Column("outcome_refs", sa.JSON(), nullable=False),
        sa.Column("verification_refs", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("generation_lineage", sa.JSON(), nullable=False),
        sa.Column("is_independent_source", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("actor", sa.String(length=64), server_default="kairo_system", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_provenances_prov_id", "memory_provenances", ["provenance_id"])
    op.create_index("ix_memory_provenances_mem_id", "memory_provenances", ["memory_id"])

    # 3. Memory Conflicts
    op.create_table(
        "memory_conflicts",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("conflict_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("memory_a_id", sa.String(length=64), nullable=False),
        sa.Column("memory_b_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="CONFLICTED", nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("temporal_context", sa.JSON(), nullable=False),
        sa.Column("environment_context", sa.JSON(), nullable=False),
        sa.Column("resolution_type", sa.String(length=64), nullable=True),
        sa.Column("resolved_by", sa.String(length=64), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_conflicts_conf_id", "memory_conflicts", ["conflict_id"])
    op.create_index("ix_memory_conflicts_mem_a", "memory_conflicts", ["memory_a_id"])
    op.create_index("ix_memory_conflicts_mem_b", "memory_conflicts", ["memory_b_id"])
    op.create_index("ix_memory_conflicts_status", "memory_conflicts", ["status"])
    op.create_index("ix_memory_conflicts_tenant_status", "memory_conflicts", ["tenant_id", "status"])

    # 4. Memory Consolidations
    op.create_table(
        "memory_consolidations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("consolidation_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("consolidated_memory_id", sa.String(length=64), nullable=True),
        sa.Column("source_memory_ids", sa.JSON(), nullable=False),
        sa.Column("abstraction_level", sa.String(length=32), nullable=False),
        sa.Column("suggested_summary", sa.Text(), nullable=False),
        sa.Column("common_entities", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("validated_by", sa.String(length=64), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_consolidations_cons_id", "memory_consolidations", ["consolidation_id"])
    op.create_index("ix_memory_consolidations_cand_id", "memory_consolidations", ["candidate_id"])
    op.create_index("ix_memory_consolidations_res_id", "memory_consolidations", ["consolidated_memory_id"])
    op.create_index("ix_memory_consolidations_status", "memory_consolidations", ["status"])

    # 5. Memory Audit Logs
    op.create_table(
        "memory_audit_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("audit_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=64), server_default="system", nullable=False),
        sa.Column("previous_state", sa.String(length=32), nullable=True),
        sa.Column("new_state", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_audit_logs_audit_id", "memory_audit_logs", ["audit_id"])
    op.create_index("ix_memory_audit_logs_mem_id", "memory_audit_logs", ["memory_id"])
    op.create_index("ix_memory_audit_logs_event_type", "memory_audit_logs", ["event_type"])
    op.create_index("ix_memory_audit_logs_timestamp", "memory_audit_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("memory_audit_logs")
    op.drop_table("memory_consolidations")
    op.drop_table("memory_conflicts")
    op.drop_table("memory_provenances")
    op.drop_table("durable_memories")
