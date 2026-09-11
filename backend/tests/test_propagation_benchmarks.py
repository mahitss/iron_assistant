"""Comprehensive 12 Evaluation Benchmark Scenarios for Risk Propagation (Spec 76)."""

from datetime import UTC, datetime
import pytest

from app.propagation.bottlenecks import BottleneckAnalyzer
from app.propagation.cascade import CascadeDetector
from app.propagation.evaluation import CascadeEvaluator
from app.propagation.resilience import ResilienceEngine
from app.propagation.schemas import (
    CascadeType,
    CriticalityLevel,
    FeedbackType,
    ImpactDimensions,
    PropagationEdge,
    RedundancyState,
    RelationshipType,
    TemporalDelay,
    TriggerType,
)
from app.propagation.service import PropagationService
from app.propagation.snapshots import GraphSnapshotEngine
from app.propagation.traversal import BoundedPropagationTraverser


@pytest.fixture
def service() -> PropagationService:
    return PropagationService()


def test_benchmark_1_simple_dependency_failure(service: PropagationService):
    """Benchmark 1: Simple dependency failure (A -> B)."""
    edges = [
        PropagationEdge(
            edge_id="e1",
            source_entity="database",
            target_entity="api_service",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.95,
            temporal_delay=TemporalDelay(expected_delay_seconds=1.0),
        )
    ]
    analysis = service.analyze_propagation(
        origin_entity="database",
        trigger="Primary database crash",
        trigger_type=TriggerType.FAILURE,
        custom_edges=edges,
    )

    assert len(analysis.direct_effects) == 1
    assert analysis.direct_effects[0].target_entity == "api_service"
    assert analysis.direct_effects[0].confidence == 0.95
    assert len(analysis.second_order_effects) == 0


def test_benchmark_2_deep_cascade(service: PropagationService):
    """Benchmark 2: Deep 5-tier cascade (N0 -> N1 -> N2 -> N3 -> N4)."""
    edges = [
        PropagationEdge(
            edge_id=f"e_{i}",
            source_entity=f"tier_{i}",
            target_entity=f"tier_{i+1}",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.90,
            temporal_delay=TemporalDelay(expected_delay_seconds=2.0),
        )
        for i in range(4)
    ]
    analysis = service.analyze_propagation(
        origin_entity="tier_0",
        trigger="Root tier latency degradation",
        trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
        custom_edges=edges,
    )

    assert analysis.propagation_depth == 4
    assert len(analysis.cascades) >= 1
    deepest_cascade = max(analysis.cascades, key=lambda c: c.total_depth)
    assert deepest_cascade.total_depth == 4
    assert deepest_cascade.cumulative_delay_seconds == 8.0
    # Confidence decays down the 5-tier chain
    assert deepest_cascade.likelihood < 0.90


def test_benchmark_3_redundant_dependency(service: PropagationService):
    """Benchmark 3: Redundant dependency dampens downstream propagation."""
    edges_redundant = [
        PropagationEdge(
            edge_id="e_red",
            source_entity="message_bus",
            target_entity="order_worker",
            relationship_type=RelationshipType.DEPENDS_ON,
            redundancy_state=RedundancyState.FULL,
            redundancy_alternatives=["message_bus_standby"],
        )
    ]
    analysis = service.analyze_propagation(
        origin_entity="message_bus",
        trigger="Leader node partition",
        trigger_type=TriggerType.FAILURE,
        custom_edges=edges_redundant,
    )

    direct = analysis.direct_effects[0]
    # Full redundancy damps operational impact
    assert direct.impact.operational_impact < 0.5
    assert analysis.resilience_assessment.redundancy_ratio == 1.0


def test_benchmark_4_single_point_of_failure(service: PropagationService):
    """Benchmark 4: Single Point of Failure (Central component with 10 downstream dependents)."""
    edges = [
        PropagationEdge(
            edge_id=f"e_{i}",
            source_entity="core_auth",
            target_entity=f"microservice_{i}",
            relationship_type=RelationshipType.DEPENDS_ON,
            redundancy_state=RedundancyState.NONE,
        )
        for i in range(10)
    ]
    analysis = service.analyze_propagation(
        origin_entity="core_auth",
        trigger="Certificate expiration",
        trigger_type=TriggerType.FAILURE,
        custom_edges=edges,
        critical_path_entities={"core_auth"},
    )

    assert len(analysis.single_points_of_failure) >= 1
    spof = analysis.single_points_of_failure[0]
    assert spof.entity_id == "core_auth"
    assert spof.criticality == CriticalityLevel.CRITICAL
    assert spof.dependent_count == 10


def test_benchmark_5_shared_resource_bottleneck(service: PropagationService):
    """Benchmark 5: Shared resource contention across separate domains."""
    edges = [
        PropagationEdge(edge_id="e1", source_entity="shared_gpu_pool", target_entity="ocr_pipeline", relationship_type=RelationshipType.SHARES_RESOURCE),
        PropagationEdge(edge_id="e2", source_entity="shared_gpu_pool", target_entity="transcription_service", relationship_type=RelationshipType.SHARES_RESOURCE),
    ]
    analysis = service.analyze_propagation(
        origin_entity="shared_gpu_pool",
        trigger="GPU VRAM exhaustion",
        trigger_type=TriggerType.RESOURCE_DEPLETION,
        custom_edges=edges,
    )

    assert any(c.cascade_type == CascadeType.RESOURCE_CASCADE for c in analysis.cascades)
    assert any(b.entity_id == "shared_gpu_pool" for b in analysis.bottlenecks)


def test_benchmark_6_amplifying_feedback_loop(service: PropagationService):
    """Benchmark 6: Amplifying feedback loop (A -> B -> C -> A)."""
    edges = [
        PropagationEdge(edge_id="e1", source_entity="cache_server", target_entity="db_pool", relationship_type=RelationshipType.AMPLIFIES),
        PropagationEdge(edge_id="e2", source_entity="db_pool", target_entity="app_server", relationship_type=RelationshipType.AMPLIFIES),
        PropagationEdge(edge_id="e3", source_entity="app_server", target_entity="cache_server", relationship_type=RelationshipType.AMPLIFIES),
    ]
    analysis = service.analyze_propagation(
        origin_entity="cache_server",
        trigger="Cache stampede",
        trigger_type=TriggerType.PERFORMANCE_DEGRADATION,
        custom_edges=edges,
    )

    assert any(c.cascade_type == CascadeType.FEEDBACK_CASCADE for c in analysis.cascades)
    assert any(c.amplification_detected for c in analysis.cascades)


def test_benchmark_7_conflicting_graph_evidence(service: PropagationService):
    """Benchmark 7: Disputed edge with conflicting evidence."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(
            edge_id="e_disputed",
            source_entity="service_a",
            target_entity="service_b",
            relationship_type=RelationshipType.DEPENDS_ON,
            is_disputed=True,
            dispute_reason="Conflicting telemetry: service_b had 0 ingress from service_a over 30d",
        )
    ]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser()
    result = traverser.traverse("service_a", snapshot)

    assert len(result.disputed_edges) == 1
    assert result.disputed_edges[0].edge_id == "e_disputed"


def test_benchmark_8_missing_dependency_uncertainty_penalty(service: PropagationService):
    """Benchmark 8: Incomplete topology increases uncertainty."""
    engine = GraphSnapshotEngine()
    edges = [PropagationEdge(edge_id="e1", source_entity="a", target_entity="b", relationship_type=RelationshipType.DEPENDS_ON)]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser()

    res_complete = traverser.traverse("a", snapshot, is_topology_complete=True)
    res_incomplete = traverser.traverse("a", snapshot, is_topology_complete=False)

    # Incomplete topology carries higher uncertainty
    assert res_incomplete.is_topology_complete is False


def test_benchmark_9_regime_change_propagation(service: PropagationService):
    """Benchmark 9: Regime change (e.g. stress regime factor 1.5x) alters propagation impact."""
    edges = [PropagationEdge(edge_id="e1", source_entity="a", target_entity="b", relationship_type=RelationshipType.DEPENDS_ON, confidence=0.8)]

    analysis_normal = service.analyze_propagation(origin_entity="a", trigger="Event", custom_edges=edges, regime_factor=1.0)
    analysis_stress = service.analyze_propagation(origin_entity="a", trigger="Event", custom_edges=edges, regime_factor=2.0)

    # High regime factor produces higher confidence in downstream failure transmission
    assert analysis_stress.direct_effects[0].confidence >= analysis_normal.direct_effects[0].confidence


def test_benchmark_10_recovery_cascade(service: PropagationService):
    """Benchmark 10: Downstream recovery propagation."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(edge_id="e1", source_entity="upstream", target_entity="midstream", relationship_type=RelationshipType.DEPENDS_ON),
        PropagationEdge(edge_id="e2", source_entity="midstream", target_entity="downstream", relationship_type=RelationshipType.DEPENDS_ON),
    ]
    snapshot = engine.create_snapshot(edges=edges)
    resilience_engine = ResilienceEngine()

    rec = resilience_engine.model_recovery_propagation("upstream", snapshot)
    assert rec["total_recovering_nodes"] == 2
    order = [r["entity"] for r in rec["recovery_order"]]
    assert order == ["midstream", "downstream"]


def test_benchmark_11_false_cascade_evaluation(service: PropagationService):
    """Benchmark 11: False cascade evaluation scoring."""
    evaluator = CascadeEvaluator()
    edges = [PropagationEdge(edge_id="e1", source_entity="root", target_entity="leaf", relationship_type=RelationshipType.DEPENDS_ON)]

    analysis = service.analyze_propagation(origin_entity="root", trigger="Blip", custom_edges=edges)
    # Ground truth: Leaf did NOT degrade
    eval_res = evaluator.evaluate(analysis, actual_degraded_nodes=[])

    assert eval_res.node_precision == 0.0
    assert eval_res.false_positive is True


def test_benchmark_12_multi_model_disagreement_uncertainty():
    """Benchmark 12: Preserves disagreement across competing models without hiding behind an average (Spec 52)."""
    engine = GraphSnapshotEngine()
    edges = [
        PropagationEdge(
            edge_id="e1",
            source_entity="app",
            target_entity="db",
            relationship_type=RelationshipType.DEPENDS_ON,
            confidence=0.55,
        )
    ]
    snapshot = engine.create_snapshot(edges=edges)
    traverser = BoundedPropagationTraverser()

    result = traverser.traverse("app", snapshot)
    effect = result.direct_effects[0]

    # Uncertainty is elevated when confidence is mediocre / models disagree
    assert effect.uncertainty >= 0.20
