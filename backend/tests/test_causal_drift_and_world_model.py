"""Tests for Feedback Loops, Threshold Effects, Causal Drift, and World Model Learning (Task 73, Spec 16, 22, 29, 30, 47, 48)."""

from app.causal.discovery_schemas import (
    CausalRelationship,
    CausalRelationshipState,
    CausalStrength,
    EdgeRelationshipType,
    EffectDirection,
    ThresholdSegment,
)
from app.causal.drift_detector import CausalDriftDetector
from app.causal.world_model_bridge import WorldModelBridge


def test_feedback_loop_representation():
    """Support cyclic causal structures (FEEDBACK_LOOP)."""
    # Cycle: Traffic -> CPU -> Latency -> Retries -> Traffic
    rel_feedback = CausalRelationship(
        cause_entity="Retries",
        cause_variable="count",
        effect_entity="Traffic",
        effect_variable="qps",
        relationship_type=EdgeRelationshipType.FEEDBACK_LOOP,
        direction=EffectDirection.POSITIVE,
        mechanism="Downstream retry storms generate amplification feedback loop",
        status=CausalRelationshipState.SUPPORTED,
        evidence_refs=["ev_retry_amplification"],
    )

    assert rel_feedback.relationship_type == EdgeRelationshipType.FEEDBACK_LOOP
    assert rel_feedback.direction == EffectDirection.POSITIVE


def test_threshold_effect_segmentation():
    """Support threshold behavior (e.g. CPU 0-70% normal, 70-90% increasing, 90%+ severe)."""
    thresholds = [
        ThresholdSegment(lower_bound=0.0, upper_bound=70.0, behavior="normal_latency", impact_multiplier=1.0),
        ThresholdSegment(lower_bound=70.0, upper_bound=90.0, behavior="increasing_latency", impact_multiplier=2.5),
        ThresholdSegment(lower_bound=90.0, upper_bound=100.0, behavior="severe_latency", impact_multiplier=10.0),
    ]

    rel = CausalRelationship(
        cause_entity="Host",
        cause_variable="cpu_load",
        effect_entity="APIGateway",
        effect_variable="latency_p99",
        direction=EffectDirection.THRESHOLD,
        thresholds=thresholds,
    )

    assert rel.direction == EffectDirection.THRESHOLD
    assert len(rel.thresholds) == 3
    assert rel.thresholds[2].behavior == "severe_latency"
    assert rel.thresholds[2].impact_multiplier == 10.0


def test_causal_drift_detection_environment_shift():
    """Detect when empirical relationship behavior shifts in a new environment."""
    detector = CausalDriftDetector(prediction_error_threshold=0.25)

    rel = CausalRelationship(
        causal_relation_id="rel_staging_tested",
        cause_entity="Pool",
        cause_variable="workers",
        effect_entity="Queue",
        effect_variable="drain_rate",
        strength=CausalStrength.STRONG,  # Expected magnitude ~ 1.0
        environment="STAGING",
        status=CausalRelationshipState.VERIFIED,
    )

    # Observed magnitude in PRODUCTION is only 0.2 (80% drop)
    drift = detector.evaluate_relationship_drift(
        relationship=rel,
        new_observations=[{"drain_rate": 0.2}],
        observed_effect_magnitude=0.2,
        environment="PRODUCTION",
    )

    assert drift is not None
    assert drift.drift_type == "CAUSAL_DRIFT"
    assert drift.prediction_error >= 0.8
    assert "Context shift: STAGING -> PRODUCTION" in drift.recommended_action


def test_world_model_drift_prediction_feedback():
    """High prediction error triggers WORLD_MODEL_DRIFT and review."""
    detector = CausalDriftDetector(prediction_error_threshold=0.20)

    rel = CausalRelationship(
        causal_relation_id="rel_cache_hit",
        cause_entity="Cache",
        cause_variable="hit_ratio",
        effect_entity="DB",
        effect_variable="qps",
        status=CausalRelationshipState.VERIFIED,
    )

    # Model predicted delta of -500 qps, actual delta was -100 qps
    predicted = {"delta": -500.0}
    actual = {"delta": -100.0}

    error, exceeds, report = detector.evaluate_prediction_feedback(
        relationship=rel,
        predicted_effect=predicted,
        actual_effect=actual,
    )

    assert exceeds is True
    assert error == 0.8
    assert report is not None
    assert report.drift_type == "WORLD_MODEL_DRIFT"
    assert "Triggering causal model review" in report.recommended_action


def test_world_model_bridge_sync_and_digital_twin():
    """Verify World Model synchronization and digital twin simulation labeling."""
    rel = CausalRelationship(
        causal_relation_id="rel_verified_sync_01",
        cause_entity="svc_gateway",
        cause_variable="rate_limit",
        effect_entity="svc_payment",
        effect_variable="throughput_tps",
        status=CausalRelationshipState.VERIFIED,
        confidence=0.94,
        verification_refs=["verif_perf_suite"],
    )

    # 1. Sync to World Model
    sync_res = WorldModelBridge.sync_to_world_model(rel)
    assert sync_res.get("synced") is True
    assert sync_res.get("relationship_type") == "CAUSES"

    # 2. Digital Twin simulation: Invariant - Clearly labeled SIMULATED_STATE, distinct from reality
    sim_res = WorldModelBridge.run_digital_twin_counterfactual(
        relationship=rel,
        baseline_state={"throughput_tps": 400.0},
        intervened_cause_value=1000,
    )
    assert sim_res["is_simulation"] is True
    assert sim_res["simulation_label"] == "SIMULATED_STATE"
    assert sim_res["simulated_value"] > 400.0
