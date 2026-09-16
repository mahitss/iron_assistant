"""Autonomous knowledge consolidation, memory reconstruction, conflict resolution and context evolution engine tables (Task 92).

Revision ID: 0060_autonomous_knowledge_consolidation_and_memory_evolution
Revises: 0059_autonomous_capability_lifecycle_and_evolution_engine
Create Date: 2026-09-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0060_autonomous_knowledge_consolidation_and_memory_evolution"
down_revision: str | None = "0059_autonomous_capability_lifecycle_and_evolution_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Memory Evidence
    op.create_table(
        "memory_evidence",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("evidence_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("relation_type", sa.String(length=32), server_default="SUPPORT", nullable=False),
        sa.Column("source", sa.String(length=256), nullable=False),
        sa.Column("source_type", sa.String(length=64), server_default="OBSERVED", nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reliability", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("freshness", sa.String(length=32), server_default="FRESH", nullable=False),
        sa.Column("provenance_id", sa.String(length=64), nullable=True),
        sa.Column("verification_status", sa.String(length=32), server_default="VERIFIED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_evidence_evidence_id", "memory_evidence", ["evidence_id"])
    op.create_index("ix_memory_evidence_memory_id", "memory_evidence", ["memory_id"])
    op.create_index("ix_memory_evidence_tenant_id", "memory_evidence", ["tenant_id"])
    op.create_index("ix_memory_evidence_relation", "memory_evidence", ["relation_type"])
    op.create_index("ix_mem_evi_mem_relation", "memory_evidence", ["memory_id", "relation_type"])

    # 2. Memory Hypotheses
    op.create_table(
        "memory_hypotheses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("hypothesis_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PROPOSED", nullable=False),
        sa.Column("validation_plan", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("supporting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("contradicting_evidence_ids", sa.JSON(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_hypotheses_hyp_id", "memory_hypotheses", ["hypothesis_id"])
    op.create_index("ix_memory_hypotheses_memory_id", "memory_hypotheses", ["memory_id"])
    op.create_index("ix_memory_hypotheses_status", "memory_hypotheses", ["status"])

    # 3. Memory Procedural
    op.create_table(
        "memory_procedural",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("procedure_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("prerequisites", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("expected_outputs", sa.JSON(), nullable=False),
        sa.Column("failure_conditions", sa.JSON(), nullable=False),
        sa.Column("validation_history", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("last_successful_execution_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capability_ref", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_procedural_proc_id", "memory_procedural", ["procedure_id"])
    op.create_index("ix_memory_procedural_memory_id", "memory_procedural", ["memory_id"])
    op.create_index("ix_memory_procedural_capability", "memory_procedural", ["capability_ref"])

    # 4. Memory Derived Links
    op.create_table(
        "memory_derived_links",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("derived_memory_id", sa.String(length=64), nullable=False),
        sa.Column("parent_memory_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("derivation_method", sa.String(length=128), server_default="deductive_inference", nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("invalidation_propagated", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_memory_derived_derived_id", "memory_derived_links", ["derived_memory_id"])
    op.create_index("ix_memory_derived_parent_id", "memory_derived_links", ["parent_memory_id"])
    op.create_index("ix_memory_derived_pair", "memory_derived_links", ["derived_memory_id", "parent_memory_id"])

    # 5. Memory Revalidation Jobs
    op.create_table(
        "memory_revalidation_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("job_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("trigger_reason", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="SCHEDULED", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mem_revalidation_job_id", "memory_revalidation_jobs", ["job_id"])
    op.create_index("ix_mem_revalidation_mem_id", "memory_revalidation_jobs", ["memory_id"])
    op.create_index("ix_mem_revalidation_status", "memory_revalidation_jobs", ["status"])

    # 6. Memory Retention Decisions
    op.create_table(
        "memory_retention_decisions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("decision_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("memory_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("importance_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("utility_score", sa.Float(), server_default="0.5", nullable=False),
        sa.Column("storage_cost", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mem_retention_decision_id", "memory_retention_decisions", ["decision_id"])
    op.create_index("ix_mem_retention_memory_id", "memory_retention_decisions", ["memory_id"])


def downgrade() -> None:
    op.drop_table("memory_retention_decisions")
    op.drop_table("memory_revalidation_jobs")
    op.drop_table("memory_derived_links")
    op.drop_table("memory_procedural")
    op.drop_table("memory_hypotheses")
    op.drop_table("memory_evidence")
