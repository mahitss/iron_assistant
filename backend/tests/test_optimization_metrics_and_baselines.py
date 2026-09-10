"""Unit tests for Optimization Metrics Engine, Statistical Aggregation, and Baseline Management (Task 62)."""

from datetime import datetime, timezone

from app.optimization.baselines import BaselineManager
from app.optimization.metrics import MetricsEngine
from app.optimization.schemas import MetricMeasurement


def test_metrics_aggregation_percentiles_and_sufficiency():
    """Verify metrics engine correctly computes mean, p50, p95, p99, and enforces sample size sufficiency."""
    engine = MetricsEngine()

    # Before inserting samples, sufficiency is False and sample count is 0
    agg_empty = engine.aggregate_metric("latency_ms")
    assert agg_empty.sample_count == 0
    assert agg_empty.has_sufficient_data is False

    # Insert 3 samples (latency_ms requires 5 samples)
    now = datetime.now(timezone.utc)
    for val in [100.0, 200.0, 300.0]:
        engine.record_measurement(
            MetricMeasurement(
                measurement_id=f"m_{val}",
                metric_name="latency_ms",
                value=val,
                timestamp=now,
                source="telemetry_agent",
                scope="production",
            )
        )

    agg_partial = engine.aggregate_metric("latency_ms")
    assert agg_partial.sample_count == 3
    assert agg_partial.has_sufficient_data is False  # Min required is 5

    # Insert 2 more samples to reach 5 samples
    for val in [400.0, 500.0]:
        engine.record_measurement(
            MetricMeasurement(
                measurement_id=f"m_{val}",
                metric_name="latency_ms",
                value=val,
                timestamp=now,
                source="telemetry_agent",
                scope="production",
            )
        )

    agg_full = engine.aggregate_metric("latency_ms")
    assert agg_full.sample_count == 5
    assert agg_full.has_sufficient_data is True
    assert agg_full.min_value == 100.0
    assert agg_full.max_value == 500.0
    assert agg_full.mean == 300.0
    assert agg_full.p50 == 300.0
    assert agg_full.p95 > 450.0
    assert agg_full.freshness_seconds >= 0.0


def test_metrics_max_history_retention():
    """Verify metrics buffer retains up to max_history elements without unbounded growth."""
    engine = MetricsEngine(max_history_per_metric=10)
    now = datetime.now(timezone.utc)

    for i in range(25):
        engine.record_measurement(
            MetricMeasurement(
                measurement_id=f"m_{i}",
                metric_name="error_rate",
                value=float(i) * 0.01,
                timestamp=now,
                source="test",
            )
        )

    agg = engine.aggregate_metric("error_rate")
    assert agg.sample_count == 10
    # Values should be from i=15 to i=24
    assert agg.min_value == 0.15


def test_baseline_manager_initialization_and_versioning():
    """Verify default baselines are loaded and updates correctly increment version."""
    manager = BaselineManager()

    base = manager.get_baseline("latency_ms")
    assert base is not None
    assert base.baseline_value == 450.0
    assert base.version == 1
    assert base.is_quarantined is False

    # Perform nominal baseline update
    updated = manager.update_baseline(
        metric_name="latency_ms",
        new_mean=420.0,
        std_dev=30.0,
        sample_count=200,
        is_incident_active=False,
    )

    assert updated.version == 2
    assert updated.baseline_value == 420.0
    assert updated.is_quarantined is False


def test_baseline_anti_poisoning_quarantine():
    """Test Invariant 10, 12: Baselines must NEVER silently update during an active incident."""
    manager = BaselineManager()

    initial = manager.get_baseline("cost_usd")
    assert initial.baseline_value == 8.5
    assert initial.version == 1

    # Attempt update while an incident is active
    quarantined = manager.update_baseline(
        metric_name="cost_usd",
        new_mean=99.0,  # Spiked abnormal cost
        std_dev=25.0,
        sample_count=50,
        is_incident_active=True,
    )

    # Must be quarantined
    assert quarantined.is_quarantined is True
    # The active baseline value must not be accepted as a clean operational target
    active = manager.get_baseline("cost_usd")
    assert active.is_quarantined is True


def test_baseline_statistical_drift_detection():
    """Verify drift detection triggers when observed value deviates by more than threshold sigmas."""
    manager = BaselineManager()

    # latency_ms default baseline: value=450, std_dev=35
    # A value of 470 is within 1 sigma -> no drift
    no_drift = manager.detect_baseline_drift("latency_ms", observed_mean=470.0, threshold_sigmas=2.5)
    assert no_drift is None

    # A value of 600 is (600 - 450) / 35 = 4.28 sigmas -> drift detected
    drift = manager.detect_baseline_drift("latency_ms", observed_mean=600.0, threshold_sigmas=2.5)
    assert drift is not None
    assert drift["is_drift_detected"] is True
    assert drift["divergence_sigmas"] >= 4.0
