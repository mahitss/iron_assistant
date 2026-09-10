"""Incident response and recovery autonomy engine tables (Task 61).

Revision ID: 0041_incident_response_and_recovery_autonomy
Revises: 0040_situational_awareness_and_event_correlation
Create Date: 2026-09-10 23:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0041_incident_response_and_recovery_autonomy"
down_revision: str | None = "0040_situational_awareness_and_event_correlation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Incident Responses Table
    op.create_table(
        "incident_responses",
        sa.Column("response_id", sa.String(length=64), primary_key=True),
        sa.Column("incident_id", sa.String(length=64), unique=True, nullable=False),
        sa.Column("situation_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="DETECTED"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("urgency", sa.String(length=32), nullable=False, server_default="NORMAL"),
        sa.Column("environment", sa.String(length=64), nullable=False, server_default="development"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("affected_resources", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("affected_services", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("affected_plans", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("affected_goals", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("responders", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("incident_commander", sa.String(length=128), nullable=True),
        sa.Column("selected_option_id", sa.String(length=64), nullable=True),
        sa.Column("automation_level", sa.String(length=32), nullable=False, server_default="RECOMMEND"),
        sa.Column("timeline", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incident_responses_response_id", "incident_responses", ["response_id"])
    op.create_index("ix_incident_responses_incident_id", "incident_responses", ["incident_id"])
    op.create_index("ix_incident_responses_situation_id", "incident_responses", ["situation_id"])
    op.create_index("ix_incident_responses_status", "incident_responses", ["status"])
    op.create_index("ix_incident_responses_severity", "incident_responses", ["severity"])
    op.create_index("ix_incident_responses_environment", "incident_responses", ["environment"])

    # 2. Incident Hypotheses Table
    op.create_table(
        "incident_hypotheses",
        sa.Column("hypothesis_id", sa.String(length=64), primary_key=True),
        sa.Column("incident_id", sa.String(length=64), sa.ForeignKey("incident_responses.incident_id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_cause", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PROPOSED"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("evidence_supporting", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence_contradictory", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("recommended_diagnostics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_hypotheses_hypothesis_id", "incident_hypotheses", ["hypothesis_id"])
    op.create_index("ix_incident_hypotheses_incident_id", "incident_hypotheses", ["incident_id"])

    # 3. Incident Actions Table
    op.create_table(
        "incident_actions",
        sa.Column("action_id", sa.String(length=64), primary_key=True),
        sa.Column("incident_id", sa.String(length=64), sa.ForeignKey("incident_responses.incident_id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PROPOSED"),
        sa.Column("is_reversible", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_idempotent", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("executor_role", sa.String(length=64), nullable=False, server_default="OPERATOR"),
        sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("verification_spec", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("execution_result", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_incident_actions_action_id", "incident_actions", ["action_id"])
    op.create_index("ix_incident_actions_incident_id", "incident_actions", ["incident_id"])

    # 4. Incident Recovery Plans Table
    op.create_table(
        "incident_recovery_plans",
        sa.Column("plan_id", sa.String(length=64), primary_key=True),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NOT_STARTED"),
        sa.Column("steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("current_step_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checkpoints", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("rollback_strategy", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_recovery_plans_plan_id", "incident_recovery_plans", ["plan_id"])
    op.create_index("ix_incident_recovery_plans_incident_id", "incident_recovery_plans", ["incident_id"])

    # 5. Incident Postmortems Table
    op.create_table(
        "incident_postmortems",
        sa.Column("postmortem_id", sa.String(length=64), primary_key=True),
        sa.Column("incident_id", sa.String(length=64), sa.ForeignKey("incident_responses.incident_id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("impact_summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.String(length=256), nullable=False, server_default="ROOT_CAUSE_UNKNOWN"),
        sa.Column("contributing_factors", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("what_worked", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("what_failed", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("action_items", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("lessons_learned", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_postmortems_postmortem_id", "incident_postmortems", ["postmortem_id"])
    op.create_index("ix_incident_postmortems_incident_id", "incident_postmortems", ["incident_id"])

    # 6. Incident Audits Table
    op.create_table(
        "incident_audits",
        sa.Column("audit_id", sa.String(length=64), primary_key=True),
        sa.Column("incident_id", sa.String(length=64), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_incident_audits_audit_id", "incident_audits", ["audit_id"])
    op.create_index("ix_incident_audits_incident_id", "incident_audits", ["incident_id"])


def downgrade() -> None:
    op.drop_table("incident_audits")
    op.drop_table("incident_postmortems")
    op.drop_table("incident_recovery_plans")
    op.drop_table("incident_actions")
    op.drop_table("incident_hypotheses")
    op.drop_table("incident_responses")
