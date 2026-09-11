"""Result Analysis, Anomaly Detection, and Epistemic Verification (Task 72).

Strictly compares pre-execution predictions against empirical observations.
Enforces fundamental distinctions:
- Result vs Interpretation
- Experiment Failure vs Hypothesis Disproof
- Invalidation vs Falsification
- Correlation vs Causation
- Environment-specific results vs Universal Generalization
"""

import uuid

from app.discovery.schemas import (
    AnalysisOutcome,
    ExperimentObservation,
    ExperimentResult,
    GeneralizationScope,
    PreExecutionPrediction,
)


class ResultAnalyzer:
    """Analyzes experiment outputs against pre-execution predictions without epistemic corruption."""

    def analyze_results(
        self,
        experiment_id: str,
        predictions: list[PreExecutionPrediction],
        observations: list[ExperimentObservation],
        controls_intact: bool = True,
        confounders_detected: list[str] | None = None,
        environment_valid: bool = True,
        measurement_error: str | None = None,
    ) -> ExperimentResult:
        """Compares predictions with observations and generates an immutable ExperimentResult."""
        res_id = f"res_{uuid.uuid4().hex[:12]}"
        confounders = confounders_detected or []

        # 1. Check for Experiment Invalidation first
        # Section 22: If controls missing, environment corrupted or measurement failed -> INVALID
        if not controls_intact or not environment_valid or bool(measurement_error) or len(confounders) > 2:
            reasons = []
            if not controls_intact:
                reasons.append("Control variables violated during run")
            if not environment_valid:
                reasons.append("Environment altered unexpectedly during execution")
            if measurement_error:
                reasons.append(f"Measurement defective: {measurement_error}")
            if len(confounders) > 2:
                reasons.append(f"Dominated by confounders: {', '.join(confounders)}")

            return ExperimentResult(
                result_id=res_id,
                experiment_id=experiment_id,
                outcome=AnalysisOutcome.INCONCLUSIVE,
                is_valid=False,
                invalidation_reason="; ".join(reasons),
                prediction_vs_observation_summary="Experiment invalidated prior to epistemic evaluation.",
                effect_size=0.0,
                unexpected_anomaly_detected=False,
                new_hypotheses=[],
                replication_status="SINGLE_RUN",
                generalization_scope=GeneralizationScope.ENVIRONMENT_SPECIFIC,
                conclusions=[
                    "Experiment setup was invalid; this outcome does NOT disprove the tested hypothesis."
                ],
            )

        if not observations:
            return ExperimentResult(
                result_id=res_id,
                experiment_id=experiment_id,
                outcome=AnalysisOutcome.INCONCLUSIVE,
                is_valid=False,
                invalidation_reason="No empirical observations captured.",
                prediction_vs_observation_summary="Observation stream was empty.",
                effect_size=0.0,
                unexpected_anomaly_detected=False,
                new_hypotheses=[],
                replication_status="SINGLE_RUN",
                generalization_scope=GeneralizationScope.ENVIRONMENT_SPECIFIC,
                conclusions=["Inconclusive due to missing measurement."],
            )

        # 2. Evaluate predictions vs observations
        # Extract numerical / directional delta where applicable
        first_pred = predictions[0] if predictions else None
        expected_dir = first_pred.expected_direction.lower() if first_pred else "decrease"

        # Calculate observation delta / direction
        values: list[float] = []
        for obs in observations:
            if isinstance(obs.value, (int, float)):
                values.append(float(obs.value))
            elif isinstance(obs.value, dict) and "delta" in obs.value:
                try:
                    values.append(float(obs.value["delta"]))
                except (ValueError, TypeError):
                    pass

        actual_dir = "neutral"
        mean_val = 0.0
        if values:
            mean_val = sum(values) / len(values)
            if mean_val > 0.05:
                actual_dir = "increase"
            elif mean_val < -0.05:
                actual_dir = "decrease"
            else:
                actual_dir = "neutral"

        # Determine outcome
        outcome = AnalysisOutcome.INCONCLUSIVE
        unexpected_anomaly = False
        new_hypotheses: list[str] = []

        if expected_dir in {"decrease", "lower", "reduce"}:
            if actual_dir == "decrease":
                outcome = AnalysisOutcome.SUPPORTED
            elif actual_dir == "increase":
                outcome = AnalysisOutcome.UNEXPECTED
                unexpected_anomaly = True
                new_hypotheses.append(
                    "Observed opposite effect: intervention triggered an unforeseen counter-mechanism or compensatory load."
                )
            else:
                outcome = AnalysisOutcome.CONTRADICTED

        elif expected_dir in {"increase", "higher", "raise"}:
            if actual_dir == "increase":
                outcome = AnalysisOutcome.SUPPORTED
            elif actual_dir == "decrease":
                outcome = AnalysisOutcome.UNEXPECTED
                unexpected_anomaly = True
                new_hypotheses.append(
                    "Observed opposite effect: intervention suppressed target metric instead of elevating it."
                )
            else:
                outcome = AnalysisOutcome.CONTRADICTED
        else:
            outcome = AnalysisOutcome.WEAKLY_SUPPORTED

        summary = (
            f"Predicted direction: '{expected_dir}', actual observed direction: '{actual_dir}' "
            f"(mean metric value: {mean_val:.4f})."
        )

        conclusions = [
            f"Hypothesis {first_pred.hypothesis_id if first_pred else 'under test'} is {outcome.value} by empirical data.",
            "Scope limited to tested environment: results must not be universally applied without cross-environment replication.",
        ]

        if unexpected_anomaly:
            conclusions.append(
                "Discovered unexpected anomaly: generated candidate explanation for follow-up testing."
            )

        return ExperimentResult(
            result_id=res_id,
            experiment_id=experiment_id,
            outcome=outcome,
            prediction_vs_observation_summary=summary,
            effect_size=abs(mean_val),
            unexpected_anomaly_detected=unexpected_anomaly,
            new_hypotheses=new_hypotheses,
            new_hypotheses_suggested=new_hypotheses,
            is_valid=True,
            invalidation_reason=None,
            replication_status="SINGLE_RUN",
            generalization_scope=GeneralizationScope.ENVIRONMENT_SPECIFIC,
            conclusions=conclusions,
        )
