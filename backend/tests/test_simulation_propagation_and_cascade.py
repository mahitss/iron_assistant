"""Unit tests for dependency topology, effect calculation, bounded propagation, and cascade failures (Task 56)."""


from app.simulation.dependencies import DependencyBridge
from app.simulation.effects import EffectCalculator
from app.simulation.propagation import EffectPropagator
from app.simulation.schemas import EffectType, SimulatedEffect, SimulatedIntervention


def test_dependency_bridge_topology_and_blast_radius():
    bridge = DependencyBridge()
    # Topology: Gateway -> Auth -> DB
    #                    -> Billing -> Stripe
    topology = {
        "gateway": ["auth", "billing"],
        "auth": ["user_db"],
        "billing": ["stripe_api"],
        "user_db": [],
        "stripe_api": [],
    }

    # Blast radius from gateway
    blast_gw = bridge.estimate_blast_radius("gateway", topology, max_depth=4)
    assert blast_gw.impacted_services_count == 4
    assert set(blast_gw.affected_nodes) == {"auth", "billing", "user_db", "stripe_api"}
    assert blast_gw.blast_radius_level == "MODERATE"
    assert blast_gw.topology_completeness == 1.0

    # Incomplete topology blast radius
    blast_partial = bridge.estimate_blast_radius("gateway", topology, max_depth=4, is_topology_partial=True)
    assert blast_partial.topology_completeness < 1.0
    assert blast_partial.uncertainty_note is not None


def test_cascade_failure_detection():
    bridge = DependencyBridge()
    topology = {
        "auth_service": ["gateway", "order_service"],
        "order_service": ["payment_worker"],
    }

    # Fatal kill on auth_service
    cascade = bridge.detect_cascades(
        origin_node="auth_service",
        is_fatal_failure=True,
        topology=topology,
        max_depth=4,
    )
    assert cascade.is_cascade_likely is True
    assert "order_service" in cascade.failing_nodes
    assert "payment_worker" in cascade.failing_nodes
    assert cascade.cascade_depth >= 2


def test_effect_calculator_across_types():
    calc = EffectCalculator()

    # 1. Kill service -> Health effect
    int_kill = SimulatedIntervention(
        intervention_id="i1",
        target="auth_service",
        operation="KILL_SERVICE",
        before={},
        hypothetical_after={},
    )
    effs_kill = calc.calculate_effects(int_kill, baseline_state={})
    health_eff = next((e for e in effs_kill if e.effect_type == EffectType.HEALTH), None)
    assert health_eff is not None
    assert health_eff.magnitude < 0
    assert "PREDICTED, NOT OBSERVED" in health_eff.mechanism

    # 2. Scale service -> Latency, Throughput, Resource, and Cost
    int_scale = SimulatedIntervention(
        intervention_id="i2",
        target="web_service",
        operation="SCALE_UP",
        before={},
        hypothetical_after={"replicas": 5},
    )
    effs_scale = calc.calculate_effects(int_scale, baseline_state={})
    cost_eff = next((e for e in effs_scale if e.effect_type == EffectType.COST), None)
    assert cost_eff is not None
    assert cost_eff.confidence <= 0.70  # Prompt #37: Cost uncertainty flagged, no false exactness

    # 3. Security disclaimer
    int_sec = SimulatedIntervention(
        intervention_id="i3",
        target="firewall",
        operation="CONFIG_SECURITY",
        before={},
        hypothetical_after={},
    )
    effs_sec = calc.calculate_effects(int_sec, baseline_state={})
    sec_eff = next((e for e in effs_sec if e.effect_type == EffectType.SECURITY), None)
    assert sec_eff is not None
    assert "Simulation cannot certify security" in sec_eff.mechanism


def test_bounded_effect_propagation_and_confidence_decay():
    propagator = EffectPropagator(max_depth=3, decay_factor=0.90)

    # Primary effect on gateway
    primary = [
        SimulatedEffect(
            effect_id="e1",
            source="test",
            target="gateway",
            effect_type=EffectType.LATENCY,
            magnitude=100.0,
            confidence=1.0,
            evidence=["primary test injection"],
            mechanism="injection",
        )
    ]

    # Topology: gateway -> service_a -> service_b -> service_c -> service_d (depth 4)
    topology = {
        "gateway": ["service_a"],
        "service_a": ["service_b"],
        "service_b": ["service_c"],
        "service_c": ["service_d"],
    }

    propagated = propagator.propagate_effects(primary, topology)
    # Bounded to max_depth 3: primary (gateway) + service_a (depth 1) + service_b (depth 2) + service_c (depth 3)
    # service_d is depth 4, so it should NOT be reached
    targets_reached = {e.target for e in propagated}
    assert "service_a" in targets_reached
    assert "service_b" in targets_reached
    assert "service_c" in targets_reached
    assert "service_d" not in targets_reached

    # Verify confidence decay
    eff_a = next(e for e in propagated if e.target == "service_a")
    eff_b = next(e for e in propagated if e.target == "service_b")
    assert eff_a.confidence > eff_b.confidence
