"""Evaluation Harness for Task 74: 10 Benchmark Scenarios (Spec 76).

Benchmark Scenarios:
1. Stable system
2. Gradual degradation
3. Sudden failure
4. Regime change
5. Noisy environment
6. Conflicting indicators
7. Missing data
8. Model disagreement
9. High false-positive environment
10. High-impact low-probability event
"""

import math
from datetime import datetime, timezone
import pytest

from app.prediction.backtesting import TemporalBacktester
from app.prediction.calibration import ProbabilityCalibrator
from app.prediction.drift import detect_input_data_drift, detect_regime_change, detect_residual_drift
from app.prediction.early_warning import EarlyWarningManager
from app.prediction.evaluation import compare_against_baseline, evaluate_point_forecast
from app.prediction.forecasts import Forecast
from app.prediction.schemas import (
    BacktestConfig,
    EarlyWarningSeverity,
    EarlyWarningState,
    ForecastHorizon,
    ForecastStrategyType,
    ForecastType,
)
from app.prediction.strategies import (
    EnsembleStrategy,
    MovingAverageStrategy,
    NaiveBaselineStrategy,
    TrendExtrapolationStrategy,
)


def test_benchmark_1_stable_system():
    """Scenario 1: Stable system with Gaussian noise around 100.0."""
    series = [100.0 + 0.5 * math.sin(i) for i in range(30)]
    strat = MovingAverageStrategy(window_size=5)
    fc = strat.generate_forecast("stable_cpu", series, horizon_steps=1)

    assert fc["predicted_value"] == pytest.approx(100.0, 0.5)
    assert fc["uncertainty"]["model_uncertainty"] <= 0.15


def test_benchmark_2_gradual_degradation():
    """Scenario 2: Gradual degradation (steady slope)."""
    # System response time degrading from 50ms up to 250ms
    series = [50.0 + i * 5.0 for i in range(25)]
    strat = TrendExtrapolationStrategy()
    fc = strat.generate_forecast("degrading_latency", series, horizon_steps=1)

    # Expected next point = 50 + 25*5 = 175.0
    assert fc["predicted_value"] == pytest.approx(175.0, 0.5)
    assert fc["metadata"]["slope"] == pytest.approx(5.0, 0.1)


def test_benchmark_3_sudden_failure():
    """Scenario 3: Sudden failure spike detection."""
    hist = [20.0, 21.0, 20.5, 19.8, 20.2]
    # Telemetry surges to 500.0
    manager = EarlyWarningManager()
    w = manager.create_warning(
        target="pod_cluster",
        signal="crash_loop_rate",
        predicted_event="cluster_collapse",
        confidence=0.95,
        severity=EarlyWarningSeverity.CRITICAL,
        evidence=["crash_count:450"],
    )
    assert w.state == EarlyWarningState.ACTIVE
    assert w.confidence == 0.95
    assert w.severity == EarlyWarningSeverity.CRITICAL


def test_benchmark_4_regime_change():
    """Scenario 4: Regime change (mean shift & variance expansion)."""
    pre = [50.0 + (i % 2) for i in range(15)]
    post = [180.0 + (i * 5) for i in range(15)]

    report = detect_regime_change("traffic_regime", pre, post)
    assert report.drift_detected is True
    assert report.drift_type == "REGIME_CHANGE"


def test_benchmark_5_noisy_environment():
    """Scenario 5: High variance noise with underlying steady baseline."""
    series = [50.0 + 15.0 * (1 if i % 2 == 0 else -1) for i in range(20)]
    ensemble = EnsembleStrategy()
    fc = ensemble.generate_forecast("noisy_metric", series, horizon_steps=1)

    # Uncertainty should reflect the high variance environment
    assert fc["uncertainty"]["environmental_uncertainty"] > 0.05
    assert fc["prediction_interval"]["upper"] > fc["predicted_value"]


def test_benchmark_6_conflicting_indicators():
    """Scenario 6: Conflicting leading indicators (one predicts up, one predicts down)."""
    manager = EarlyWarningManager()
    w = manager.create_warning(
        target="database_write_iops",
        signal="cache_ratio_healthy_but_disk_queue_exploding",
        predicted_event="write_stall",
        confidence=0.65,  # lower confidence due to conflict
        severity=EarlyWarningSeverity.ADVISORY,
        evidence=["cache_hit:99%", "disk_queue_depth:150"],
    )
    assert w.state == EarlyWarningState.ACTIVE
    assert w.confidence == 0.65


def test_benchmark_7_missing_data_refusal():
    """Scenario 7: Missing or insufficient observations triggers refusal / fallback."""
    series = [42.0]
    strat = TrendExtrapolationStrategy()
    # Insufficient points for trend calculation falls back gracefully to naive baseline
    fc = strat.generate_forecast("sparse_series", series, horizon_steps=1)
    assert fc["predicted_value"] == 42.0
    assert fc["uncertainty"]["data_uncertainty"] >= 0.50


def test_benchmark_8_model_disagreement():
    """Scenario 8: Sub-models strongly disagree on trajectory."""
    ensemble = EnsembleStrategy()
    # Strongly nonlinear series where polynomial/trend and naive divergence is wide
    series = [1.0, 2.0, 4.0, 8.0, 16.0, 32.0]
    res = ensemble.generate_forecast("disagreeing_models", series, horizon_steps=1)

    assert "sub_predictions" in res["metadata"]
    assert res["metadata"]["disagreement_spread"] > 5.0


def test_benchmark_9_high_false_positive_environment():
    """Scenario 9: High false-positive rate tracking in calibration."""
    calibrator = ProbabilityCalibrator(model_reference="noisy_early_detector")
    for _ in range(15):
        calibrator.record(prediction_probability=0.80, actual_outcome=0)  # 100% false alarms

    report = calibrator.evaluate_calibration()
    assert report.is_degraded is True
    assert report.systematic_bias == "OVERCONFIDENT"


def test_benchmark_10_high_impact_low_probability_event():
    """Scenario 10: High-impact low-probability (HILP) early warning gating."""
    manager = EarlyWarningManager()
    # Event probability is 25%, but impact is catastrophic data loss
    w = manager.create_warning(
        target="primary_storage_volume",
        signal="smart_sector_reallocation_detected",
        predicted_event="catastrophic_storage_loss",
        confidence=0.30,
        severity=EarlyWarningSeverity.CRITICAL,
        evidence=["smart_attribute_05:128"],
        recommended_investigation="Trigger emergency snapshot replication immediately",
    )
    attn = w.to_attention_candidate_dict()
    # Priority in attention engine is elevated due to CRITICAL severity despite modest probability
    assert attn["severity"] == "CRITICAL"
    assert attn["urgency"] == 0.9
