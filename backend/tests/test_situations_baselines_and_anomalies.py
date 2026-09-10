"""Unit tests for Baseline Engine, Anti-Poisoning Quarantine, and Anomaly Detection (Task 60)."""

from app.situational_awareness.anomaly import AnomalyDetector
from app.situational_awareness.baselines import BaselineEngine
from app.situational_awareness.schemas import AnomalySignal, SignalBaseline, SituationSeverity


def test_baseline_incremental_calibration():
    """Verify that healthy observations incrementally update baseline mean, min, max, and sample count."""
    engine = BaselineEngine()
    # Initial observation
    b1 = engine.record_observation("cpu_usage", "server-1", 40.0, environment="production")
    assert b1.sample_count == 1
    assert b1.mean_val == 40.0

    # Add 10 observations between 40 and 60
    for val in [42.0, 48.0, 50.0, 52.0, 58.0, 45.0, 47.0, 55.0, 43.0]:
        engine.record_observation("cpu_usage", "server-1", val, environment="production")

    updated = engine.get_baseline("cpu_usage", "server-1", environment="production")
    assert updated is not None
    assert updated.sample_count == 10
    assert 40.0 <= updated.mean_val <= 60.0
    assert updated.min_val == 40.0
    assert updated.max_val == 58.0


def test_baseline_anti_poisoning_quarantine_during_incident():
    """Test Invariant 21: Active incident periods MUST NOT poison operational baselines."""
    engine = BaselineEngine()

    # Establish clean baseline
    for _ in range(15):
        engine.record_observation("memory_usage", "db-node", 30.0, environment="production")

    clean_baseline = engine.get_baseline("memory_usage", "db-node", environment="production")
    clean_mean = clean_baseline.mean_val
    clean_count = clean_baseline.sample_count

    # Inject extreme spike during an active incident
    engine.record_observation(
        "memory_usage",
        "db-node",
        99.9,
        environment="production",
        is_incident_period=True,
    )

    quarantined = engine.get_baseline("memory_usage", "db-node", environment="production")
    assert quarantined.sample_count == clean_count
    assert quarantined.mean_val == clean_mean
    assert quarantined.max_val < 90.0  # Spike was rejected


def test_anomaly_detection_with_sigma_deviation():
    """Verify that observations exceeding sigma threshold are flagged with appropriate confidence."""
    baseline_eng = BaselineEngine()
    # Pre-populate baseline: mean=50, std_dev=5, count=20
    b = SignalBaseline(
        signal_name="latency_ms",
        resource="api-gateway",
        environment="production",
        mean_val=50.0,
        std_dev=5.0,
        sample_count=20,
    )
    baseline_eng.register_baseline(b)

    detector = AnomalyDetector(baselines=baseline_eng)

    # Within normal variation (55ms = 1 sigma)
    normal = detector.check_observation("latency_ms", "api-gateway", 55.0, environment="production")
    assert normal is None

    # Significant anomaly (80ms = (80-50)/5 = 6 sigmas)
    anomaly = detector.check_observation("latency_ms", "api-gateway", 80.0, environment="production")
    assert anomaly is not None
    assert anomaly.deviation_sigmas == 6.0
    assert anomaly.confidence >= 0.90


def test_multi_signal_corroboration_escalates_confidence():
    """Test Invariant 38: Combining independent signals boosts confidence without double-counting identical sources."""
    detector = AnomalyDetector()

    anom1 = AnomalySignal(
        signal_name="cpu_spike",
        resource="app-service",
        observed_value=95.0,
        baseline_mean=40.0,
        deviation_sigmas=4.5,
        confidence=0.85,
    )
    anom2 = AnomalySignal(
        signal_name="500_error_rate",
        resource="app-service",
        observed_value=12.0,
        baseline_mean=0.5,
        deviation_sigmas=4.2,
        confidence=0.80,
    )

    single_eval = detector.corroborate_anomalies([anom1])
    assert not single_eval["is_corroborated"]
    assert single_eval["distinct_signals_count"] == 1

    multi_eval = detector.corroborate_anomalies([anom1, anom2])
    assert multi_eval["is_corroborated"]
    assert multi_eval["distinct_signals_count"] == 2
    assert multi_eval["confidence"] > single_eval["confidence"]
    assert multi_eval["suggested_severity"] in (SituationSeverity.HIGH, SituationSeverity.CRITICAL)


def test_false_positive_control_for_weak_isolated_signals():
    """Verify weak isolated signals do not result in critical incident suggestions."""
    detector = AnomalyDetector()
    weak_anom = AnomalySignal(
        signal_name="minor_jitter",
        resource="cache",
        observed_value=12.0,
        baseline_mean=10.0,
        deviation_sigmas=3.0,
        confidence=0.60,
    )
    eval_res = detector.corroborate_anomalies([weak_anom])
    assert eval_res["suggested_severity"] == SituationSeverity.MEDIUM
    assert not eval_res["is_corroborated"]
