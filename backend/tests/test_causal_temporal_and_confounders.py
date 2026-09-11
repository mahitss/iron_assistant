"""Tests for Temporal Causality, Causal Lag, Confounders, Mediators, and Colliders (Task 73, Spec 11, 12, 13, 14, 15)."""

from datetime import datetime, timedelta, timezone

from app.causal.confounder_engine import ConfounderEngine
from app.causal.temporal_engine import TemporalCausalityEngine


def test_temporal_precedence_valid_order_and_lag():
    """Verify that cause preceding effect is valid and correctly computes causal lag."""
    t0 = datetime(2026, 9, 12, 10, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(minutes=20)

    res = TemporalCausalityEngine.validate_temporal_precedence(cause_time=t0, effect_time=t1)
    assert res.is_temporally_valid is True
    assert res.contradiction_detected is False
    assert res.lag_seconds == 1200.0  # 20 minutes lag
    assert res.contradiction_reason is None


def test_temporal_contradiction_effect_before_cause():
    """Invariant: Surface contradiction when suspected effect occurred before cause."""
    # Deployment at 10:00, latency increase started at 09:50
    t_cause = datetime(2026, 9, 12, 10, 0, 0, tzinfo=timezone.utc)
    t_effect = datetime(2026, 9, 12, 9, 50, 0, tzinfo=timezone.utc)

    res = TemporalCausalityEngine.validate_temporal_precedence(cause_time=t_cause, effect_time=t_effect)
    assert res.is_temporally_valid is False
    assert res.contradiction_detected is True
    assert "Temporal Contradiction" in (res.contradiction_reason or "")
    assert "BEFORE suspected cause" in (res.contradiction_reason or "")


def test_confounder_detection_common_cause():
    """Invariant: Common cause Z affecting both X and Y reduces causal confidence and flags confounding."""
    # Knowledge graph: Traffic -> CPU and Traffic -> Latency
    known_edges = [
        {
            "cause_entity": "Traffic",
            "cause_variable": "qps",
            "effect_entity": "Host",
            "effect_variable": "cpu_load",
            "evidence_refs": ["ev_load_test"],
        },
        {
            "cause_entity": "Traffic",
            "cause_variable": "qps",
            "effect_entity": "APIGateway",
            "effect_variable": "latency_ms",
            "evidence_refs": ["ev_gateway_telemetry"],
        },
    ]

    # Evaluate correlation between Host.cpu_load and APIGateway.latency_ms
    analysis = ConfounderEngine.analyze_confounders(
        cause_entity="Host",
        cause_var="cpu_load",
        effect_entity="APIGateway",
        effect_var="latency_ms",
        known_edges=known_edges,
        initial_confidence=0.85,
    )

    assert analysis.is_confounded is True
    assert "Traffic:qps" in analysis.common_causes
    assert analysis.confidence_penalty > 0.0
    assert analysis.adjusted_confidence < 0.85
    assert "Potential confounding detected via common cause" in analysis.recommendation


def test_mediator_analysis_indirect_mechanism():
    """Invariant: Detect mediating chains X -> M -> Y to explain mechanism."""
    # Traffic -> CPU -> Latency
    known_edges = [
        {
            "cause_entity": "Traffic",
            "cause_variable": "qps",
            "effect_entity": "Host",
            "effect_variable": "cpu_load",
        },
        {
            "cause_entity": "Host",
            "cause_variable": "cpu_load",
            "effect_entity": "APIGateway",
            "effect_variable": "latency_ms",
        },
    ]

    res = ConfounderEngine.analyze_mediators(
        cause_entity="Traffic",
        cause_var="qps",
        effect_entity="APIGateway",
        effect_var="latency_ms",
        known_edges=known_edges,
    )

    assert res.is_mediated is True
    assert "Host:cpu_load" in res.mediator_variables
    assert res.indirect_paths == [["Traffic:qps", "Host:cpu_load", "APIGateway:latency_ms"]]
    assert "Mediated mechanism detected" in res.mechanism_narrative


def test_collider_bias_warning():
    """Invariant: Conditioning on common effect A -> C <- B generates collider warning."""
    # A -> C and B -> C
    known_edges = [
        {
            "cause_entity": "FactorA",
            "cause_variable": "v1",
            "effect_entity": "CommonEffect",
            "effect_variable": "collider_node",
        },
        {
            "cause_entity": "FactorB",
            "cause_variable": "v2",
            "effect_entity": "CommonEffect",
            "effect_variable": "collider_node",
        },
    ]

    res = ConfounderEngine.detect_colliders(
        cause_a="FactorA:v1",
        cause_b="FactorB:v2",
        conditioned_on="CommonEffect:collider_node",
        known_edges=known_edges,
    )

    assert res.is_conditioned is True
    assert res.warning is not None
    assert "Collider Conditioning Warning" in res.warning
