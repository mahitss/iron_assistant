"""Migration for Simulation & Counterfactual Planning Engine (Task 56).

Revision ID: 0036_simulation_and_counterfactual_planning
Revises: 0035_causal_reasoning_and_causal_graph
Create Date: 2026-09-15 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_simulation_and_counterfactual_planning"
down_revision: str | None = "0035_causal_reasoning_and_causal_graph"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. simulation_snapshots
    op.create_table(
        "simulation_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("source_entity", sa.String(length=128), nullable=False, server_default="digital_twin"),
        sa.Column("world_state", sa.JSON(), nullable=False),
        sa.Column("digital_twin_state", sa.JSON(), nullable=False),
        sa.Column("telemetry_state", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("baseline_hash", sa.String(length=64), nullable=False),
        sa.Column("is_stale", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("staleness_reason", sa.String(length=256), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id"),
    )
    op.create_index("ix_simulation_snapshots_snapshot_id", "simulation_snapshots", ["snapshot_id"])
    op.create_index("ix_simulation_snapshots_baseline_hash", "simulation_snapshots", ["baseline_hash"])
    op.create_index("ix_ssnap_source_ts", "simulation_snapshots", ["source_entity", "captured_at"])

    # 2. simulation_scenarios
    op.create_table(
        "simulation_scenarios",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("scenario_type", sa.String(length=64), nullable=False, server_default="CUSTOM"),
        sa.Column("baseline_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("interventions", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("objectives", sa.JSON(), nullable=False),
        sa.Column("horizon", sa.String(length=64), nullable=False, server_default="SHORT_TERM"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="CREATED"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id"),
    )
    op.create_index("ix_simulation_scenarios_scenario_id", "simulation_scenarios", ["scenario_id"])
    op.create_index("ix_simulation_scenarios_baseline_id", "simulation_scenarios", ["baseline_snapshot_id"])
    op.create_index("ix_scen_type_status", "simulation_scenarios", ["scenario_type", "status"])

    # 3. simulations
    op.create_table(
        "simulations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("simulation_id", sa.String(length=64), nullable=False),
        sa.Column("source_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("initial_state", sa.JSON(), nullable=False),
        sa.Column("future_state", sa.JSON(), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=False),
        sa.Column("effects", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("assumptions", sa.JSON(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="CREATED"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("environment_label", sa.String(length=64), nullable=False, server_default="SIMULATION_ONLY"),
        sa.Column("is_hypothetical", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("simulation_id"),
    )
    op.create_index("ix_simulations_simulation_id", "simulations", ["simulation_id"])
    op.create_index("ix_simulations_source_snapshot_id", "simulations", ["source_snapshot_id"])
    op.create_index("ix_simulations_scenario_id", "simulations", ["scenario_id"])
    op.create_index("ix_sim_status", "simulations", ["status"])
    op.create_index("ix_sim_created_at", "simulations", ["created_at"])

    # 4. simulation_execution_gates
    op.create_table(
        "simulation_execution_gates",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("gate_id", sa.String(length=64), nullable=False),
        sa.Column("simulation_id", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="BLOCKED"),
        sa.Column("baseline_snapshot_id", sa.String(length=64), nullable=False),
        sa.Column("baseline_hash_at_sim", sa.String(length=64), nullable=False),
        sa.Column("current_hash", sa.String(length=64), nullable=True),
        sa.Column("drift_detected", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("drift_details", sa.JSON(), nullable=False),
        sa.Column("verification_plan", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gate_id"),
    )
    op.create_index("ix_simulation_execution_gates_gate_id", "simulation_execution_gates", ["gate_id"])
    op.create_index("ix_simulation_execution_gates_simulation_id", "simulation_execution_gates", ["simulation_id"])
    op.create_index("ix_gate_status", "simulation_execution_gates", ["status"])

    # 5. simulation_calibrations
    op.create_table(
        "simulation_calibrations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("calibration_id", sa.String(length=64), nullable=False),
        sa.Column("simulation_id", sa.String(length=64), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("predicted_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("actual_value", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("bias", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("calibrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("calibration_id"),
    )
    op.create_index("ix_simulation_calibrations_calibration_id", "simulation_calibrations", ["calibration_id"])
    op.create_index("ix_cal_metric", "simulation_calibrations", ["metric_name"])
    op.create_index("ix_cal_sim_id", "simulation_calibrations", ["simulation_id"])


def downgrade() -> None:
    op.drop_table("simulation_calibrations")
    op.drop_table("simulation_execution_gates")
    op.drop_table("simulations")
    op.drop_table("simulation_scenarios")
    op.drop_table("simulation_snapshots")
