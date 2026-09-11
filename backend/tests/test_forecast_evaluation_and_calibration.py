"""Unit tests for Forecast Evaluation Metrics and Calibration Engine (Task 74, Spec 13, 14, 43, 67, 68)."""

import pytest

from app.prediction.calibration import ProbabilityCalibrator
from app.prediction.evaluation import (
    compare_against_baseline,
    evaluate_early_warning,
    evaluate_interval_forecast,
    evaluate_point_forecast,
    evaluate_probabilistic_forecast,
)
from app.prediction.schemas import PredictionInterval


def test_point_forecast_evaluation_metrics():
    """Verify MAE, RMSE, sMAPE, and directional accuracy computations (Spec 13)."""
    predictions = [10.0, 12.0, 15.0, 14.0]
    actuals = [11.0, 11.0, 16.0, 13.0]
    previous = [9.0, 10.0, 12.0, 15.0]

    eval_res = evaluate_point_forecast(predictions, actuals, previous)

    assert eval_res["count"] == 4
    assert eval_res["mae"] == pytest.approx(1.0, 0.05)
    assert eval_res["rmse"] == pytest.approx(1.0, 0.05)
    assert eval_res["smape"] > 0.0
    assert eval_res["directional_accuracy"] == 1.0  # all predicted directions matched actuals


def test_interval_forecast_coverage_and_width():
    """Verify prediction interval coverage and interval width (Spec 7, 13)."""
    intervals = [
        PredictionInterval(lower=8.0, upper=12.0, coverage_target=0.90),
        PredictionInterval(lower=10.0, upper=14.0, coverage_target=0.90),
        PredictionInterval(lower=18.0, upper=22.0, coverage_target=0.90),
    ]
    actuals = [10.0, 15.0, 20.0]  # 1st covered, 2nd missed, 3rd covered -> 2/3 = 66.7%

    res = evaluate_interval_forecast(intervals, actuals)

    assert res["count"] == 3
    assert res["coverage_rate"] == pytest.approx(2.0 / 3.0, 0.01)
    assert res["mean_interval_width"] == pytest.approx(4.0, 0.01)


def test_probabilistic_brier_and_log_loss():
    """Verify proper scoring rules: Brier score and log loss (Spec 13)."""
    # Well-calibrated predictions
    probs = [0.9, 0.1, 0.8, 0.2]
    outcomes = [1, 0, 1, 0]

    res = evaluate_probabilistic_forecast(probs, outcomes)

    assert res["brier_score"] == pytest.approx(0.025, 0.005)
    assert res["log_loss"] < 0.3
    assert res["count"] == 4


def test_baseline_comparison_and_msss():
    """Verify Mean Squared Skill Score relative to baseline (Spec 9, 13)."""
    comp = compare_against_baseline(
        model_errors=[1.0, 1.0, 1.0],
        baseline_errors=[2.0, 2.0, 2.0],
    )
    # MSE model = 1.0, MSE base = 4.0 -> MSSS = 1 - (1/4) = 0.75
    assert comp["model_mse"] == 1.0
    assert comp["baseline_mse"] == 4.0
    assert comp["msss"] == pytest.approx(0.75, 0.01)
    assert comp["outperformed_baseline"] is True


def test_early_warning_metrics():
    """Verify precision, recall, false-positive rate, and lead time stats (Spec 13, 67, 68)."""
    warnings = [
        {"warning_id": "w1", "lead_time_seconds": 120.0, "is_critical": True},
        {"warning_id": "w2", "lead_time_seconds": 60.0, "is_critical": False},
    ]
    outcomes = [
        {"warning_id": "w1", "confirmed": True},
        {"warning_id": "w2", "confirmed": False},
        {"warning_id": "w_missed", "confirmed": True},  # missed
    ]

    res = evaluate_early_warning(warnings, outcomes)

    assert res["warnings_count"] == 2
    assert res["confirmed_count"] == 1
    assert res["precision"] == 0.5  # 1 confirmed out of 2 warnings
    assert res["lead_time_stats"]["mean_lead_time_seconds"] == 120.0


def test_calibration_deciles_and_ece_computation():
    """Verify ProbabilityCalibrator decile binning, ECE, MCE, and bias detection (Spec 14)."""
    calibrator = ProbabilityCalibrator(model_reference="gpt-4o-predict")

    # Record predictions with systematic overconfidence:
    # Model predicts 0.85, but events only happen 50% of the time (Spec 14)
    for i in range(20):
        actual = 1 if i % 2 == 0 else 0
        calibrator.record(prediction_probability=0.85, actual_outcome=actual)

    report = calibrator.evaluate_calibration()

    assert report.model_reference == "gpt-4o-predict"
    assert report.sample_size == 20
    assert report.expected_calibration_error > 0.20
    assert len(report.buckets) == 10

    # Verify systematic bias detection
    assert report.systematic_bias == "OVERCONFIDENT"
    assert report.is_degraded is True  # ECE > 0.25 threshold
