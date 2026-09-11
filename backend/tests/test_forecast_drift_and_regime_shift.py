"""Unit tests for Forecast Drift Detection, Regime Shift, and Health Classification (Task 74, Spec 21, 23, 64)."""

import pytest

from app.prediction.drift import (
    ForecastDriftDetector,
    ForecastHealthStatus,
    detect_calibration_drift,
    detect_input_data_drift,
    detect_regime_change,
    detect_residual_drift,
)


def test_input_data_drift_detection():
    """Verify Kolmogorov-Smirnov-style mean shift detection on incoming distribution (Spec 23)."""
    baseline = [10.0, 10.2, 9.8, 10.1, 9.9, 10.0, 10.3, 9.7]
    shifted = [18.0, 19.5, 17.8, 18.2, 19.0, 18.5, 17.9, 18.8]

    report = detect_input_data_drift(target="cache_miss_rate", baseline_sample=baseline, current_sample=shifted)

    assert report.drift_detected is True
    assert report.drift_type == "INPUT_DATA_DRIFT"
    assert report.p_value_or_score > 0.0


def test_residual_error_drift_detection():
    """Verify residual drift triggers when recent error exceeds 2.5 standard deviations (Spec 23)."""
    # Historical errors around 1.0
    hist_errors = [1.0, 1.2, 0.9, 1.1, 1.0, 0.8, 1.1, 0.9, 1.0, 1.2]
    # Recent surge in error to 5.0
    recent_errors = [4.5, 5.2, 4.8, 5.0]

    report = detect_residual_drift(target="response_time", historical_errors=hist_errors, recent_errors=recent_errors)

    assert report.drift_detected is True
    assert report.drift_type == "RESIDUAL_DRIFT"
    assert "Residual error drift" in report.description


def test_calibration_drift_detection():
    """Verify calibration degradation detected when Brier score increases by >40% (Spec 23)."""
    baseline_brier = 0.10
    degraded_brier = 0.22  # >100% increase

    report = detect_calibration_drift(target="failure_event", baseline_brier=baseline_brier, current_brier=degraded_brier)

    assert report.drift_detected is True
    assert report.drift_type == "CALIBRATION_DRIFT"
    assert "Calibration degraded" in report.description


def test_regime_change_sudden_shift_and_variance_surge():
    """Verify regime change detects mean displacement and variance explosion (Spec 21)."""
    pre_shift = [100.0, 101.0, 99.5, 100.5, 100.2, 99.8]
    post_shift = [250.0, 310.0, 180.0, 290.0, 340.0, 210.0]  # high mean + massive variance

    report = detect_regime_change(target="traffic_volume", pre_window=pre_shift, post_window=post_shift)

    assert report.drift_detected is True
    assert report.drift_type == "REGIME_CHANGE"


def test_forecast_health_status_classification():
    """Verify health transitions: HEALTHY -> DRIFTING -> DEGRADED -> UNRELIABLE (Spec 64)."""
    detector = ForecastDriftDetector(target="db_latency")

    # Clean state
    assert detector.get_health_status() == ForecastHealthStatus.HEALTHY

    # Stale state
    assert detector.get_health_status(is_stale=True) == ForecastHealthStatus.STALE

    # Record small input drift -> DRIFTING
    detector.record_drift_event(
        drift_type="INPUT_DATA_DRIFT",
        score=0.15,
        description="Minor distribution change",
    )
    assert detector.get_health_status() == ForecastHealthStatus.DRIFTING

    # Record calibration degradation -> DEGRADED
    detector.record_drift_event(
        drift_type="CALIBRATION_DRIFT",
        score=0.35,
        description="Brier score increased 45%",
    )
    assert detector.get_health_status() == ForecastHealthStatus.DEGRADED

    # High error count -> UNRELIABLE
    assert detector.get_health_status(error_rate=0.45) == ForecastHealthStatus.UNRELIABLE
