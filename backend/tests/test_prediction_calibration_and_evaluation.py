import pytest
from app.prediction.calibration import (
    ProbabilityCalibrator,
    CalibrationMetrics,
    OutcomeRecord,
    OutcomeType,
)


def test_calibration_metrics_brier_and_log_loss():
    calibrator = ProbabilityCalibrator()

    # Add well-calibrated outcomes
    calibrator.record_outcome(predicted_prob=0.8, actual_outcome=1, outcome_type=OutcomeType.CORRECT)
    calibrator.record_outcome(predicted_prob=0.7, actual_outcome=1, outcome_type=OutcomeType.CORRECT)
    calibrator.record_outcome(predicted_prob=0.2, actual_outcome=0, outcome_type=OutcomeType.CORRECT)
    calibrator.record_outcome(predicted_prob=0.1, actual_outcome=0, outcome_type=OutcomeType.CORRECT)

    metrics = calibrator.compute_metrics()
    assert isinstance(metrics, CalibrationMetrics)
    assert metrics.sample_size == 4
    assert metrics.brier_score < 0.1  # Very good Brier score
    assert metrics.log_loss < 0.5


def test_small_sample_penalty():
    calibrator = ProbabilityCalibrator(min_sample_threshold=10)
    # Only 2 samples
    calibrator.record_outcome(predicted_prob=0.99, actual_outcome=1, outcome_type=OutcomeType.CORRECT)
    calibrator.record_outcome(predicted_prob=0.95, actual_outcome=1, outcome_type=OutcomeType.CORRECT)

    # Low sample size must adjust confidence downwards or flag high uncertainty
    calibrated_conf, uncertainty = calibrator.calibrate_confidence(raw_confidence=0.95, domain="system_telemetry")
    assert calibrated_conf < 0.95
    assert uncertainty > 0.2


def test_unknown_outcome_and_intervention_flag():
    calibrator = ProbabilityCalibrator()

    # Unknown outcome cannot be treated as failure / incorrect
    calibrator.record_outcome(
        predicted_prob=0.7,
        actual_outcome=None,
        outcome_type=OutcomeType.UNKNOWN,
        prediction_id="pred_unobserved_1",
    )
    records = calibrator.get_records()
    assert len(records) == 1
    assert records[0].outcome_type == OutcomeType.UNKNOWN
    # Unknown outcomes must not skew Brier score
    brier = calibrator.compute_brier_score()
    assert brier is None or brier == 0.0

    # Intervention flag: if Kairo intervened, it should not be evaluated as an untouched natural forecast
    calibrator.record_outcome(
        predicted_prob=0.85,
        actual_outcome=0,
        outcome_type=OutcomeType.INCORRECT,
        intervened=True,
        intervention_details="Scaled replicas early to avoid outage",
    )
    records = calibrator.get_records()
    assert records[1].intervened is True
    assert records[1].intervention_details == "Scaled replicas early to avoid outage"
