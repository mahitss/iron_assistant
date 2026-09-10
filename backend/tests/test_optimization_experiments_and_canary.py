"""Unit tests for Sandboxed Experiments and Phased Canary Deployments (Task 62)."""

import pytest

from app.optimization.canary import CanaryController
from app.optimization.experiments import ExperimentManager
from app.optimization.safety import OptimizationSafetyError
from app.optimization.schemas import (
    ChangeSet,
    ChangeSetStatus,
    ExperimentStatus,
    ExperimentVariant,
    RolloutState,
)


def test_experiment_lifecycle_create_approve_start():
    """Verify controlled experiment transitions through DRAFT/PROPOSED -> APPROVED -> RUNNING."""
    manager = ExperimentManager()

    variants = [
        ExperimentVariant(
            variant_id="var_high_cache",
            name="Expanded Cache",
            parameter_overrides={"cache_max_size_mb": 512.0},
            sample_allocation_pct=50.0,
        ),
        ExperimentVariant(
            variant_id="var_control",
            name="Standard Cache Control",
            parameter_overrides={"cache_max_size_mb": 256.0},
            sample_allocation_pct=50.0,
        ),
    ]

    exp = manager.create_experiment(
        hypothesis="Doubling cache size reduces p95 latency by 15%",
        target_metrics=["latency_ms"],
        control_parameters={"cache_max_size_mb": 256.0},
        variants=variants,
    )

    assert exp.status == ExperimentStatus.PROPOSED
    assert len(exp.variants) == 2

    # Cannot start directly from PROPOSED
    with pytest.raises(OptimizationSafetyError, match="must be APPROVED"):
        manager.start_experiment(exp.experiment_id)

    # Approve
    approved = manager.approve_experiment(exp.experiment_id, approver="LEAD_ENGINEER")
    assert approved.status == ExperimentStatus.APPROVED

    # Start
    started = manager.start_experiment(exp.experiment_id)
    assert started.status == ExperimentStatus.RUNNING


def test_experiment_safety_gates_and_stop_conditions():
    """Test Invariant 17: Sandboxed experiments halt immediately upon breaching safety gates."""
    manager = ExperimentManager()

    exp = manager.create_experiment(
        hypothesis="High throughput batching test",
        target_metrics=["throughput_rps"],
        control_parameters={"batch_size_items": 10.0},
        variants=[],
    )
    manager.approve_experiment(exp.experiment_id)
    manager.start_experiment(exp.experiment_id)

    # Nominal observation
    safe_obs = {"error_rate": 0.01, "latency_ms": 350.0}
    is_safe, _ = manager.evaluate_safety_gates(exp.experiment_id, safe_obs)
    assert is_safe is True
    assert manager.get_experiment(exp.experiment_id).status == ExperimentStatus.RUNNING

    # Observation with error rate breach (> 0.05)
    breach_obs = {"error_rate": 0.08, "latency_ms": 400.0}
    is_safe_breach, msg = manager.evaluate_safety_gates(exp.experiment_id, breach_obs)
    assert is_safe_breach is False
    assert "Stop condition triggered" in msg
    assert manager.get_experiment(exp.experiment_id).status == ExperimentStatus.FAILED


def test_canary_deployment_phased_advancement():
    """Test Invariant 21: Phased canary advancement strictly requires verified healthy telemetry."""
    controller = CanaryController()

    cs = ChangeSet(
        change_set_id="cs_canary_01",
        target_parameter="model_routing_latency_weight",
        before_state=0.5,
        after_state=0.7,
        reason="Reduce p95 tail latency",
        rollback_strategy="Restore model_routing_latency_weight to 0.5",
        status=ChangeSetStatus.APPROVED,
        version=1,
    )

    # Cannot initiate canary if change set is not APPROVED
    cs_unapproved = ChangeSet(
        change_set_id="cs_draft_01",
        target_parameter="cache_ttl_seconds",
        before_state=300.0,
        after_state=360.0,
        reason="Cache test",
        rollback_strategy="Restore cache_ttl_seconds to 300.0",
        status=ChangeSetStatus.DRAFT,
        version=1,
    )
    with pytest.raises(OptimizationSafetyError, match="Must be APPROVED"):
        controller.initiate_canary(cs_unapproved)

    # Initiate canary at 10%
    canary = controller.initiate_canary(cs, initial_traffic_pct=10.0)
    assert canary.rollout_state == RolloutState.CANARY_10
    assert canary.traffic_percentage == 10.0
    assert canary.is_verified is False

    # Attempting to advance without verification fails closed
    with pytest.raises(OptimizationSafetyError, match="without verified healthy telemetry"):
        controller.advance_rollout(canary.canary_id, target_state=RolloutState.CANARY_50, is_verified=False)

    # Advance to 50% with verified telemetry
    adv_50 = controller.advance_rollout(
        canary.canary_id, target_state=RolloutState.CANARY_50, is_verified=True
    )
    assert adv_50.rollout_state == RolloutState.CANARY_50
    assert adv_50.traffic_percentage == 50.0

    # Advance to FULL_ROLLOUT (100%)
    adv_full = controller.advance_rollout(
        canary.canary_id, target_state=RolloutState.FULL_ROLLOUT, is_verified=True
    )
    assert adv_full.rollout_state == RolloutState.FULL_ROLLOUT
    assert adv_full.traffic_percentage == 100.0


def test_canary_abort_and_containment():
    """Verify triggering canary abort immediately drops traffic to 0% and marks rollout as ROLLED_BACK."""
    controller = CanaryController()

    cs = ChangeSet(
        change_set_id="cs_abort_test",
        target_parameter="batch_size_items",
        before_state=10.0,
        after_state=20.0,
        reason="Increase throughput",
        rollback_strategy="Restore batch_size_items to 10.0",
        status=ChangeSetStatus.APPROVED,
        version=1,
    )

    canary = controller.initiate_canary(cs, initial_traffic_pct=10.0)
    aborted = controller.trigger_abort(canary.canary_id, reason="Telemetry degradation observed")

    assert aborted.rollout_state == RolloutState.ROLLED_BACK
    assert aborted.traffic_percentage == 0.0
    assert aborted.failure_threshold_reached is True

    # Further advancement is blocked
    with pytest.raises(OptimizationSafetyError, match="failure threshold was reached"):
        controller.advance_rollout(canary.canary_id, target_state=RolloutState.CANARY_50, is_verified=True)
