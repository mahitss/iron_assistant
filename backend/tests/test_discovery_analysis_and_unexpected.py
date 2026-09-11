"""Unit tests for Result Analysis, Invalidation, and Unexpected Results (Task 72)."""

from app.discovery.analyzer import ResultAnalyzer
from app.discovery.prediction import PredictionRecorder
from app.discovery.schemas import (
    AnalysisOutcome,
    GeneralizationScope,
)


def test_result_analysis_hypothesis_supported():
    """Prediction expected decrease; observation observed decrease -> SUPPORTED."""
    analyzer = ResultAnalyzer()
    recorder = PredictionRecorder()

    pred = recorder.record_prediction(
        experiment_id="exp_supported",
        hypothesis_id="hyp_cache_tune",
        expected_direction="decrease",
    )
    obs = recorder.record_observation(
        experiment_id="exp_supported",
        source="telemetry",
        measurement_metric="latency",
        value={"delta": -0.45},
    )

    result = analyzer.analyze_results(
        experiment_id="exp_supported",
        predictions=[pred],
        observations=[obs],
    )

    assert result.outcome == AnalysisOutcome.SUPPORTED
    assert result.is_valid is True
    assert result.unexpected_anomaly_detected is False
    assert result.generalization_scope == GeneralizationScope.ENVIRONMENT_SPECIFIC


def test_result_analysis_unexpected_result_creates_anomaly_and_hypothesis():
    """Prediction expected decrease; observation observed increase -> UNEXPECTED anomaly."""
    analyzer = ResultAnalyzer()
    recorder = PredictionRecorder()

    pred = recorder.record_prediction(
        experiment_id="exp_anomaly",
        hypothesis_id="hyp_thread_boost",
        expected_direction="decrease",
    )
    # Observed opposite direction!
    obs = recorder.record_observation(
        experiment_id="exp_anomaly",
        source="telemetry",
        measurement_metric="latency",
        value={"delta": +0.85},
    )

    result = analyzer.analyze_results(
        experiment_id="exp_anomaly",
        predictions=[pred],
        observations=[obs],
    )

    assert result.outcome == AnalysisOutcome.UNEXPECTED
    assert result.unexpected_anomaly_detected is True
    # Must generate candidate follow-up explanation
    assert len(result.new_hypotheses) > 0
    assert (
        "unforeseen counter-mechanism" in result.new_hypotheses[0]
        or "opposite effect" in result.new_hypotheses[0]
    )


def test_experiment_invalidation_does_not_refute_hypothesis():
    """Strict principle: Experiment execution failure or invalidation does NOT disprove the hypothesis."""
    analyzer = ResultAnalyzer()
    recorder = PredictionRecorder()

    pred = recorder.record_prediction(
        experiment_id="exp_invalid",
        hypothesis_id="hyp_db_index",
        expected_direction="decrease",
    )
    obs = recorder.record_observation(
        experiment_id="exp_invalid",
        source="telemetry",
        measurement_metric="query_time",
        value={"delta": +0.20},
    )

    # Controls were violated during the run
    result = analyzer.analyze_results(
        experiment_id="exp_invalid",
        predictions=[pred],
        observations=[obs],
        controls_intact=False,
    )

    assert result.is_valid is False
    assert result.outcome == AnalysisOutcome.INCONCLUSIVE
    assert "Control variables violated" in (result.invalidation_reason or "")
    # Conclusions explicitly state this does NOT disprove the hypothesis
    assert any("does NOT disprove" in c for c in result.conclusions)


def test_experiment_invalidation_on_measurement_defect():
    """Measurement failure marks experiment INVALID rather than claiming hypothesis disproof."""
    analyzer = ResultAnalyzer()
    recorder = PredictionRecorder()

    pred = recorder.record_prediction(
        experiment_id="exp_sensor_fail",
        hypothesis_id="hyp_cpu_governor",
        expected_direction="decrease",
    )

    result = analyzer.analyze_results(
        experiment_id="exp_sensor_fail",
        predictions=[pred],
        observations=[],
        measurement_error="Monitoring agent dropped packets",
    )

    assert result.is_valid is False
    assert "Monitoring agent dropped packets" in (result.invalidation_reason or "")
