"""Pre-execution Predictions and Empirical Observation Tracking (Task 72).

Enforces:
1. Immutable recording of predictions BEFORE experiment execution begins.
2. Uncorrupted capture of empirical observations (never fabricated).
3. Clear distinction between simulation runs and real-world observations.
"""

import uuid
from typing import Any

from app.discovery.schemas import (
    EnvironmentType,
    ExperimentObservation,
    PreExecutionPrediction,
)


class PredictionRecorder:
    """Records pre-execution hypotheses predictions and protects their immutability."""

    def record_prediction(
        self,
        experiment_id: str,
        hypothesis_id: str,
        expected_direction: str,
        confidence: float = 0.75,
        expected_range: str = "",
        assumptions: list[str] | None = None,
    ) -> PreExecutionPrediction:
        """Records expected outcomes strictly prior to experiment launch.

        Integrity Invariant: Predictions are immutable once stored.
        """
        p_id = f"pred_{uuid.uuid4().hex[:12]}"
        return PreExecutionPrediction(
            prediction_id=p_id,
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id,
            expected_direction=expected_direction.strip().lower(),
            expected_range=expected_range.strip(),
            confidence=max(0.0, min(1.0, float(confidence))),
            assumptions=list(assumptions or []),
            is_immutable=True,
        )

    def record_observation(
        self,
        experiment_id: str,
        source: str,
        measurement_metric: str,
        value: Any,
        unit: str = "",
        environment: EnvironmentType = EnvironmentType.STAGING,
        raw_reference: str = "",
        verification_state: str = "UNVERIFIED",
        is_simulation: bool = False,
    ) -> ExperimentObservation:
        """Captures an actual empirical measurement.

        Integrity Invariant: Never fabricate observations.
        If is_simulation is True, explicitly tags the observation as synthetic.
        """
        obs_id = f"obs_{uuid.uuid4().hex[:12]}"
        return ExperimentObservation(
            observation_id=obs_id,
            experiment_id=experiment_id,
            source=source,
            environment=environment,
            measurement_metric=measurement_metric,
            value=value,
            unit=unit,
            raw_reference=raw_reference,
            verification_state=verification_state,
            is_simulation=is_simulation,
        )
