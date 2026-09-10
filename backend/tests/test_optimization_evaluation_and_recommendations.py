"""Unit tests for Evaluation Gap Analysis and Bounded Recommendation Generation (Task 62)."""

from datetime import datetime, timezone

from app.optimization.baselines import BaselineManager
from app.optimization.evaluation import OptimizationEvaluator
from app.optimization.metrics import MetricsEngine
from app.optimization.parameters import AdjustableParameterRegistry
from app.optimization.recommendations import RecommendationGenerator
from app.optimization.schemas import MetricMeasurement, OptimizationGap


def test_gap_analysis_detects_lagging_metrics():
    """Verify OptimizationEvaluator correctly flags metrics failing to meet target values."""
    metrics_eng = MetricsEngine()
    baselines_mgr = BaselineManager()
    evaluator = OptimizationEvaluator(metrics_eng=metrics_eng, baselines_mgr=baselines_mgr)

    now = datetime.now(timezone.utc)
    # Target for latency_ms is 300.0 (MINIMIZE). Ingest 5 samples with mean 600.0
    for i in range(5):
        metrics_eng.record_measurement(
            MetricMeasurement(
                measurement_id=f"m_lat_{i}",
                metric_name="latency_ms",
                value=600.0,
                timestamp=now,
                source="test",
            )
        )

    # Target for throughput_rps is 100.0 (MAXIMIZE). Ingest 5 samples with mean 120.0 (better than target)
    for i in range(5):
        metrics_eng.record_measurement(
            MetricMeasurement(
                measurement_id=f"m_tp_{i}",
                metric_name="throughput_rps",
                value=120.0,
                timestamp=now,
                source="test",
            )
        )

    gaps = evaluator.evaluate_gaps()

    # Latency should be detected as a gap
    lat_gap = next((g for g in gaps if g.metric_name == "latency_ms"), None)
    assert lat_gap is not None
    assert lat_gap.current_value == 600.0
    assert lat_gap.target_value == 300.0
    assert lat_gap.gap_delta == 300.0
    assert lat_gap.gap_percentage == 100.0
    assert lat_gap.urgency == "HIGH"
    assert "model_routing_weights" in lat_gap.likely_contributors

    # Throughput exceeds target -> no gap
    tp_gap = next((g for g in gaps if g.metric_name == "throughput_rps"), None)
    assert tp_gap is None


def test_gap_analysis_ignores_insufficient_data():
    """Verify metrics with fewer than min_samples_required are ignored to prevent premature optimization."""
    metrics_eng = MetricsEngine()
    evaluator = OptimizationEvaluator(metrics_eng=metrics_eng)

    now = datetime.now(timezone.utc)
    # Ingest only 2 samples for latency_ms (requires 5)
    metrics_eng.record_measurement(
        MetricMeasurement(
            measurement_id="m_1", metric_name="latency_ms", value=999.0, timestamp=now, source="test"
        )
    )
    metrics_eng.record_measurement(
        MetricMeasurement(
            measurement_id="m_2", metric_name="latency_ms", value=999.0, timestamp=now, source="test"
        )
    )

    gaps = evaluator.evaluate_gaps()
    assert len(gaps) == 0


def test_recommendation_generator_produces_bounded_proposals():
    """Verify recommendation generator proposes actionable changes within bounds with explicit rollback."""
    registry = AdjustableParameterRegistry()
    generator = RecommendationGenerator(registry=registry)

    gap = OptimizationGap(
        metric_name="latency_ms",
        current_value=600.0,
        target_value=300.0,
        gap_delta=300.0,
        gap_percentage=100.0,
        likely_contributors=["model_routing_weights", "cache_ttl_sizing"],
        confidence=0.90,
        urgency="HIGH",
    )

    recs = generator.generate_recommendations([gap])
    assert len(recs) >= 1

    routing_rec = next((r for r in recs if r.target_parameter == "model_routing_latency_weight"), None)
    assert routing_rec is not None
    assert routing_rec.proposed_value > routing_rec.current_value
    assert routing_rec.rollback_strategy is not None
    assert "Restore model_routing_latency_weight" in routing_rec.rollback_strategy


def test_recommendation_generator_for_throughput_and_batching():
    """Verify recommendations for throughput propose batch size adjustment with low risk."""
    registry = AdjustableParameterRegistry()
    generator = RecommendationGenerator(registry=registry)

    gap = OptimizationGap(
        metric_name="throughput_rps",
        current_value=40.0,
        target_value=100.0,
        gap_delta=60.0,
        gap_percentage=60.0,
        likely_contributors=["batch_size_items"],
        confidence=0.85,
        urgency="HIGH",
    )

    recs = generator.generate_recommendations([gap])
    batch_rec = next((r for r in recs if r.target_parameter == "batch_size_items"), None)
    assert batch_rec is not None
    assert batch_rec.current_value == 10.0
    assert batch_rec.proposed_value == 20.0  # current (10) + max_step (10)
    assert batch_rec.requires_approval is False
