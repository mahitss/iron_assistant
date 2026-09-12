"""Autonomous resource economy, capability allocation and cognitive budget engine tables (Task 77).

Revision ID: 0057_autonomous_resource_economy_and_cognitive_budget_engine
Revises: 0056_autonomous_resilience_recovery_adaptive_defense_engine
Create Date: 2026-09-12 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0057_autonomous_resource_economy_and_cognitive_budget_engine"
down_revision: str | None = "0056_autonomous_resilience_recovery_adaptive_defense_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Cognitive Budgets
    op.create_table(
        "cognitive_budgets",
        sa.Column("budget_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=64), server_default="default_tenant", nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="GLOBAL", nullable=False),
        sa.Column("scope_id", sa.String(length=128), server_default="global", nullable=False),
        sa.Column("state", sa.String(length=32), server_default="CREATED", nullable=False),
        sa.Column("limits", sa.JSON(), nullable=False),
        sa.Column("consumed", sa.JSON(), nullable=False),
        sa.Column("reserved", sa.JSON(), nullable=False),
        sa.Column("near_limit_threshold", sa.Float(), server_default="0.85", nullable=False),
        sa.Column("reset_frequency", sa.String(length=32), server_default="NEVER", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cognitive_budgets_tenant_id", "cognitive_budgets", ["tenant_id"])
    op.create_index("ix_cognitive_budgets_scope", "cognitive_budgets", ["scope"])
    op.create_index("ix_cognitive_budgets_scope_id", "cognitive_budgets", ["scope_id"])
    op.create_index("ix_cognitive_budgets_state", "cognitive_budgets", ["state"])

    # 2. Resource Demands
    op.create_table(
        "resource_demands",
        sa.Column("demand_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("capability_id", sa.String(length=64), server_default="", nullable=False),
        sa.Column("estimated_tokens", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("model_calls", sa.Integer(), server_default="1", nullable=False),
        sa.Column("expected_time_s", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("lower_bound", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("upper_bound", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("uncertainty_pct", sa.Float(), server_default="0.15", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="0.85", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_preemptible", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resource_demands_task_id", "resource_demands", ["task_id"])
    op.create_index("ix_resource_demands_resource_id", "resource_demands", ["resource_id"])

    # 3. Task Preemptions
    op.create_table(
        "task_preemptions",
        sa.Column("preemption_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1", nullable=False),
        sa.Column("preempted_by_task_id", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=32), server_default="RUNNING", nullable=False),
        sa.Column("checkpoint_token", sa.String(length=128), nullable=True),
        sa.Column("state_snapshot", sa.JSON(), nullable=False),
        sa.Column("saved_context_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("wait_time_s", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("cost_of_preemption", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_task_preemptions_task_id", "task_preemptions", ["task_id"])
    op.create_index("ix_task_preemptions_state", "task_preemptions", ["state"])

    # 4. Resource Contention Records
    op.create_table(
        "resource_contention_records",
        sa.Column("contention_id", sa.String(length=64), primary_key=True),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("competing_tasks", sa.JSON(), nullable=False),
        sa.Column("strategy", sa.String(length=32), server_default="SEQUENCE", nullable=False),
        sa.Column("total_demanded", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("available_capacity", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("cycle_detected", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("wait_graph", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resource_contention_records_resource_id", "resource_contention_records", ["resource_id"])

    # 5. Resource Efficiency Logs
    op.create_table(
        "resource_efficiency_logs",
        sa.Column("log_id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("capability_id", sa.String(length=64), server_default="", nullable=False),
        sa.Column("model_used", sa.String(length=128), server_default="", nullable=False),
        sa.Column("tokens_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duration_ms", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("cost_estimate", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("degradation_tier", sa.String(length=32), server_default="FULL_FIDELITY", nullable=False),
        sa.Column("trade_off_scores", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resource_efficiency_logs_task_id", "resource_efficiency_logs", ["task_id"])


def downgrade() -> None:
    op.drop_table("resource_efficiency_logs")
    op.drop_table("resource_contention_records")
    op.drop_table("task_preemptions")
    op.drop_table("resource_demands")
    op.drop_table("cognitive_budgets")
