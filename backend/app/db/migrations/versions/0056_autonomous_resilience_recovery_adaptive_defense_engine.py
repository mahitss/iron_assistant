"""Autonomous resilience, recovery, containment and adaptive defense engine tables (Task 76).

Revision ID: 0056_autonomous_resilience_recovery_adaptive_defense_engine
Revises: 0055_autonomous_risk_propagation_and_cascade_engine
Create Date: 2026-09-12 01:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0056_autonomous_resilience_recovery_adaptive_defense_engine"
down_revision: str | None = "0055_autonomous_risk_propagation_and_cascade_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Resilience Assessments
    op.create_table(
        "resilience_assessments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("scope", sa.String(length=64), server_default="SYSTEM", nullable=False),
        sa.Column("target", sa.String(length=128), server_default="CORE", nullable=False),
        sa.Column("state", sa.String(length=32), server_default="ASSESSED", nullable=False),
        sa.Column("scorecard", sa.JSON(), nullable=False),
        sa.Column("identified_weaknesses", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resilience_assessments_tenant_id", "resilience_assessments", ["tenant_id"])
    op.create_index("ix_resilience_assessments_state", "resilience_assessments", ["state"])

    # 2. Resilience Gaps
    op.create_table(
        "resilience_gaps",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assessment_id", sa.String(length=64), sa.ForeignKey("resilience_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("gap_type", sa.String(length=64), nullable=False),
        sa.Column("affected_scope", sa.String(length=128), nullable=False),
        sa.Column("target_entity", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("remediation_candidate", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resilience_gaps_assessment_id", "resilience_gaps", ["assessment_id"])
    op.create_index("ix_resilience_gaps_tenant_id", "resilience_gaps", ["tenant_id"])
    op.create_index("ix_resilience_gaps_gap_type", "resilience_gaps", ["gap_type"])
    op.create_index("ix_resilience_gaps_target_entity", "resilience_gaps", ["target_entity"])
    op.create_index("ix_resilience_gaps_tenant_target", "resilience_gaps", ["tenant_id", "target_entity"])

    # 3. Recovery Plans
    op.create_table(
        "resilience_recovery_plans",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assessment_id", sa.String(length=64), sa.ForeignKey("resilience_assessments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("cascade_id", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=32), server_default="DETECTED", nullable=False),
        sa.Column("selected_strategy", sa.String(length=64), nullable=False),
        sa.Column("containment_points", sa.JSON(), nullable=False),
        sa.Column("recovery_paths", sa.JSON(), nullable=False),
        sa.Column("execution_order", sa.JSON(), nullable=False),
        sa.Column("preconditions", sa.JSON(), nullable=False),
        sa.Column("verification_criteria", sa.JSON(), nullable=False),
        sa.Column("residual_risk", sa.JSON(), nullable=True),
        sa.Column("return_to_normal_plan", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("approval_id", sa.String(length=64), nullable=True),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resilience_recovery_plans_assessment_id", "resilience_recovery_plans", ["assessment_id"])
    op.create_index("ix_resilience_recovery_plans_tenant_id", "resilience_recovery_plans", ["tenant_id"])
    op.create_index("ix_resilience_recovery_plans_incident_id", "resilience_recovery_plans", ["incident_id"])
    op.create_index("ix_resilience_recovery_plans_cascade_id", "resilience_recovery_plans", ["cascade_id"])
    op.create_index("ix_resilience_recovery_plans_state", "resilience_recovery_plans", ["state"])
    op.create_index("ix_resilience_recovery_plans_approval_id", "resilience_recovery_plans", ["approval_id"])
    op.create_index("ix_recovery_plans_tenant_state", "resilience_recovery_plans", ["tenant_id", "state"])

    # 4. Recovery Execution Steps
    op.create_table(
        "resilience_recovery_steps",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("plan_id", sa.String(length=64), sa.ForeignKey("resilience_recovery_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("action_id", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("output", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("rollback_performed", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index("ix_resilience_recovery_steps_plan_id", "resilience_recovery_steps", ["plan_id"])
    op.create_index("ix_resilience_recovery_steps_tenant_id", "resilience_recovery_steps", ["tenant_id"])
    op.create_index("ix_recovery_steps_plan_state", "resilience_recovery_steps", ["plan_id", "state"])

    # 5. Post-Incident Lessons
    op.create_table(
        "resilience_lessons",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("recovery_plan_id", sa.String(length=64), nullable=True),
        sa.Column("what_was_expected", sa.Text(), nullable=False),
        sa.Column("what_happened", sa.Text(), nullable=False),
        sa.Column("why_it_mattered", sa.Text(), nullable=False),
        sa.Column("what_should_change", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OBSERVED", nullable=False),
        sa.Column("learned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resilience_lessons_tenant_id", "resilience_lessons", ["tenant_id"])
    op.create_index("ix_resilience_lessons_incident_id", "resilience_lessons", ["incident_id"])
    op.create_index("ix_resilience_lessons_recovery_plan_id", "resilience_lessons", ["recovery_plan_id"])
    op.create_index("ix_resilience_lessons_status", "resilience_lessons", ["status"])

    # 6. Adaptive Defense Recommendations
    op.create_table(
        "resilience_adaptive_recommendations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("recommendation_type", sa.String(length=64), nullable=False),
        sa.Column("target_entity", sa.String(length=128), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.8", nullable=False),
        sa.Column("cost", sa.String(length=32), server_default="LOW", nullable=False),
        sa.Column("reversibility", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("risk_reduction", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resilience_adaptive_recommendations_tenant_id", "resilience_adaptive_recommendations", ["tenant_id"])
    op.create_index("ix_resilience_adaptive_recommendations_recommendation_type", "resilience_adaptive_recommendations", ["recommendation_type"])
    op.create_index("ix_resilience_adaptive_recommendations_target_entity", "resilience_adaptive_recommendations", ["target_entity"])
    op.create_index("ix_resilience_adaptive_recommendations_status", "resilience_adaptive_recommendations", ["status"])


def downgrade() -> None:
    op.drop_table("resilience_adaptive_recommendations")
    op.drop_table("resilience_lessons")
    op.drop_table("resilience_recovery_steps")
    op.drop_table("resilience_recovery_plans")
    op.drop_table("resilience_gaps")
    op.drop_table("resilience_assessments")
