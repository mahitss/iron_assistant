"""Unit tests for historical backtesting and zero data leakage verification (Task 75)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.propagation.backtesting import PropagationBacktester
from app.propagation.evaluation import CascadeEvaluator
from app.propagation.schemas import (
    ImpactDimensions,
    PropagationAnalysis,
    PropagationEdge,
    RelationshipType,
    TriggerType,
)
from app.propagation.snapshots import GraphSnapshotEngine


def test_cascade_evaluator_precision_and_recall():
    """Verify precision, recall, and false positive metrics on realized outcomes (Spec 59, 60)."""
    evaluator = CascadeEvaluator()

    analysis = PropagationAnalysis(
        trigger="Worker failure",
        origin_entity="worker_1",
    )
    # Mock direct effect on worker_2 and worker_3
    analysis.direct_effects = [
        type("DirectMock", (), {
            "target_entity": "worker_2",
            "impact": ImpactDimensions(operational_impact=0.8),
            "temporal_delay": type("DelayMock", (), {"expected_delay_seconds": 2.0})(),
        })(),
        type("DirectMock", (), {
            "target_entity": "worker_3",
            "impact": ImpactDimensions(operational_impact=0.5),
            "temporal_delay": type("DelayMock", (), {"expected_delay_seconds": 3.0})(),
        })(),
    ]

    # Scenario 1: Both predicted degraded
    eval_perfect = evaluator.evaluate(analysis, actual_degraded_nodes=["worker_2", "worker_3"])
    assert eval_perfect.node_precision == 1.0
    assert eval_perfect.node_recall == 1.0
    assert not eval_perfect.false_positive

    # Scenario 2: Only worker_2 degraded (worker_3 was a false node)
    eval_partial = evaluator.evaluate(analysis, actual_degraded_nodes=["worker_2"])
    assert eval_partial.node_precision == 0.5
    assert eval_partial.node_recall == 1.0
    assert "worker_3" in eval_partial.false_nodes

    # Scenario 3: Zero degraded (False positive cascade)
    eval_fp = evaluator.evaluate(analysis, actual_degraded_nodes=[])
    assert eval_fp.node_precision == 0.0
    assert len(eval_fp.false_nodes) == 2


def test_backtester_strictly_verifies_zero_future_leakage():
    """Verify backtester rejects/quarantines future edges and validates zero leakage (Spec 61, 62)."""
    engine = GraphSnapshotEngine()
    backtester = PropagationBacktester()

    t0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    t_future = datetime(2026, 1, 5, 12, 0, 0, tzinfo=UTC)

    # Edge 1: historical edge valid at t0
    # Edge 2: future architectural change after t0 (should NOT leak into analysis at t0)
    edges = [
        PropagationEdge(
            edge_id="e_hist",
            source_entity="service_x",
            target_entity="service_y",
            relationship_type=RelationshipType.DEPENDS_ON,
            valid_from=t0 - timedelta(days=5),
            valid_until=t0 + timedelta(days=2),
        ),
        PropagationEdge(
            edge_id="e_future",
            source_entity="service_y",
            target_entity="service_z",
            relationship_type=RelationshipType.DEPENDS_ON,
            valid_from=t_future,  # Created in the future relative to t0
        ),
    ]

    historical_triggers = [
        {
            "timestamp": t0,
            "origin_entity": "service_x",
            "trigger": "Initial outage",
            "trigger_type": "FAILURE",
            "actual_degraded_nodes": ["service_y"],
        }
    ]

    report = backtester.run_backtest(historical_triggers, all_edges=edges)

    assert report.zero_future_leakage_verified is True
    assert report.total_triggers_evaluated == 1
    assert report.mean_node_precision == 1.0
    assert report.mean_node_recall == 1.0
