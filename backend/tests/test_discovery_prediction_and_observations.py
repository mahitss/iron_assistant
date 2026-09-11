"""Unit tests for Pre-execution Prediction Immutability and Observation Recording (Task 72)."""

from app.discovery.prediction import PredictionRecorder
from app.discovery.schemas import EnvironmentType


def test_pre_execution_prediction_recording():
    """Verifies that predictions are formulated with explicit expectations and immutable flag."""
    recorder = PredictionRecorder()

    pred = recorder.record_prediction(
        experiment_id="exp_timeout_test",
        hypothesis_id="hyp_pool_timeout",
        expected_direction="decrease",
        confidence=0.85,
        expected_range="-100ms to -200ms",
        assumptions=["Database CPU utilization remains below 70%"],
    )

    assert pred.prediction_id.startswith("pred_")
    assert pred.expected_direction == "decrease"
    assert pred.confidence == 0.85
    assert pred.is_immutable is True
    assert len(pred.assumptions) == 1


def test_empirical_observation_recording():
    """Integrity principle: Observations capture real measurements without fabrication."""
    recorder = PredictionRecorder()

    obs = recorder.record_observation(
        experiment_id="exp_timeout_test",
        source="prometheus_metrics_cluster_staging",
        measurement_metric="p95_latency_ms",
        value={"delta": -145.2, "raw_value": 174.8},
        unit="ms",
        environment=EnvironmentType.STAGING,
        raw_reference="prometheus://query?query=histogram_quantile(0.95...)",
        verification_state="MEASURED",
        is_simulation=False,
    )

    assert obs.observation_id.startswith("obs_")
    assert obs.measurement_metric == "p95_latency_ms"
    assert obs.value["delta"] == -145.2
    assert obs.unit == "ms"
    assert obs.is_simulation is False
    assert obs.verification_state == "MEASURED"


def test_simulation_clearly_separated_from_reality():
    """Epistemic decoupling: Simulation outputs are strictly tagged is_simulation=True."""
    recorder = PredictionRecorder()

    sim_obs = recorder.record_observation(
        experiment_id="exp_synthetic_run",
        source="digital_twin_monte_carlo",
        measurement_metric="p95_latency_ms",
        value=-160.0,
        unit="ms",
        environment=EnvironmentType.SIMULATION,
        raw_reference="sim://task56/scenario_9",
        verification_state="SYNTHETIC",
        is_simulation=True,
    )

    assert sim_obs.is_simulation is True
    assert sim_obs.verification_state == "SYNTHETIC"
    assert sim_obs.environment == EnvironmentType.SIMULATION
