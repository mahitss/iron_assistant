"""Multi-horizon range forecasting, expanding uncertainty cones, ensemble calibration, and disagreement handling (Task 65, Spec 19-22, 60-64)."""

from __future__ import annotations

import logging

from app.foresight.schemas import (
    ForecastInterval,
    ForecastRecord,
    ForecastStatus,
    ForesightHorizon,
)

logger = logging.getLogger(__name__)

# Base confidence ceilings by horizon (Spec 22: Long-Horizon Uncertainty Expansion)
HORIZON_CONFIDENCE_CEILING: dict[ForesightHorizon, float] = {
    ForesightHorizon.PAST: 0.95,
    ForesightHorizon.NOW: 0.95,
    ForesightHorizon.NEAR_FUTURE_1H: 0.90,
    ForesightHorizon.NEAR_FUTURE_1D: 0.82,
    ForesightHorizon.MID_FUTURE_1W: 0.75,
    ForesightHorizon.MID_FUTURE_1M: 0.60,
    ForesightHorizon.LONG_FUTURE_1Y: 0.45,
}


class LongHorizonForecaster:
    """Generates range-based forecasts with calibrated uncertainty and multi-model consensus/disagreement (Spec 19-22)."""

    def __init__(self) -> None:
        self._forecasts: dict[str, ForecastRecord] = {}

    def generate_forecast(
        self,
        topic: str,
        horizon: ForesightHorizon = ForesightHorizon.NEAR_FUTURE_1D,
        metric_name: str | None = None,
        base_estimate: float = 100.0,
        variance_factor: float = 0.15,
        unit: str = "ms",
        assumptions: list[str] | None = None,
        evidence: list[str] | None = None,
        competing_models: dict[str, float] | None = None,
        tenant_id: str = "default",
    ) -> ForecastRecord:
        """Generate a temporal forecast with range intervals.

        Invariant: FORECAST != FACT (Spec 19, 64).
        Never output deterministic certainty for future probabilistic states.
        Invariant: NO FALSE PRECISION (Spec 20, 101). Intervals are used rather than pseudo-precise scalars.
        """
        # 1. Expand range uncertainty based on horizon
        uncertainty_multiplier = {
            ForesightHorizon.NEAR_FUTURE_1H: 1.0,
            ForesightHorizon.NEAR_FUTURE_1D: 1.5,
            ForesightHorizon.MID_FUTURE_1W: 2.2,
            ForesightHorizon.MID_FUTURE_1M: 3.5,
            ForesightHorizon.LONG_FUTURE_1Y: 5.0,
        }.get(horizon, 1.5)

        spread = base_estimate * variance_factor * uncertainty_multiplier
        lower = max(0.0, round(base_estimate - spread, 1))
        upper = round(base_estimate + spread, 1)

        interval = ForecastInterval(
            metric_name=metric_name or "metric_level",
            lower_bound=lower,
            point_estimate=round(base_estimate, 1),
            upper_bound=upper,
            unit=unit,
            confidence_level=0.90,
        )

        # 2. Confidence ceiling enforcement
        max_conf = HORIZON_CONFIDENCE_CEILING.get(horizon, 0.70)
        calibrated_conf = min(0.85, max_conf)

        # 3. Model ensemble & disagreement detection (Spec 61, 62)
        competing_hypotheses: list[str] = []
        if competing_models and len(competing_models) > 1:
            values = list(competing_models.values())
            min_val, max_val = min(values), max(values)
            divergence = (max_val - min_val) / (base_estimate or 1.0)
            if divergence > 0.30:
                # Substantial model disagreement!
                competing_hypotheses = [
                    f"Model '{m}' predicts {val:.1f}{unit}" for m, val in competing_models.items()
                ]
                calibrated_conf = round(calibrated_conf * 0.85, 2)
                summary = (
                    f"Forecast for {topic} shows divergence across {len(competing_models)} models "
                    f"({min_val:.1f} to {max_val:.1f}{unit}). Range: {lower}–{upper}{unit}."
                )
            else:
                summary = f"Consensus projection for {topic}: expected range {lower}–{upper}{unit}."
        else:
            summary = f"Projected range for {topic} over {horizon.value}: {lower}–{upper}{unit}."

        fct = ForecastRecord(
            topic=topic,
            horizon=horizon,
            intervals=[interval],
            prediction_summary=summary,
            assumptions=assumptions or ["Workload remains within historical boundaries"],
            evidence=evidence or ["Historical baseline trend extrapolation"],
            competing_hypotheses=competing_hypotheses,
            model_name="ensemble" if competing_models else "statistical_baseline",
            confidence=calibrated_conf,
            status=ForecastStatus.ACTIVE,
            tenant_id=tenant_id,
        )

        self._forecasts[fct.forecast_id] = fct
        logger.info(
            "FORECAST_GENERATED: id=%s topic='%s' horizon=%s range=%s–%s%s conf=%.2f",
            fct.forecast_id,
            topic,
            horizon.value,
            lower,
            upper,
            unit,
            calibrated_conf,
        )
        return fct

    def record_actual_outcome(self, forecast_id: str, actual_value: float) -> float:
        """Record the realized ground truth outcome and compute forecast calibration score (Spec 21, 63)."""
        fct = self._forecasts.get(forecast_id)
        if not fct:
            raise KeyError(f"Forecast '{forecast_id}' not found.")

        if not fct.intervals:
            fct.actual_outcome = f"Observed value: {actual_value}"
            fct.status = ForecastStatus.FULFILLED
            return 1.0

        intv = fct.intervals[0]
        fct.actual_outcome = f"Realized value: {actual_value} {intv.unit}"

        # Evaluate if actual value fell within the predicted range
        if intv.lower_bound <= actual_value <= intv.upper_bound:
            # High calibration
            dist = abs(actual_value - intv.point_estimate)
            spread = max(1.0, intv.upper_bound - intv.lower_bound)
            error_ratio = dist / spread
            calibration = max(0.5, round(1.0 - error_ratio, 2))
            fct.status = ForecastStatus.FULFILLED
        else:
            # Out of bounds!
            fct.status = ForecastStatus.CONTRADICTED
            dist = min(abs(actual_value - intv.lower_bound), abs(actual_value - intv.upper_bound))
            calibration = max(0.1, round(0.5 - (dist / intv.point_estimate), 2))

        fct.calibration_score = calibration
        logger.info(
            "FORECAST_CALIBRATION_RECORDED: id=%s actual=%.1f score=%.2f status=%s",
            forecast_id,
            actual_value,
            calibration,
            fct.status.value,
        )
        return calibration

    def invalidate_on_assumption_failure(self, failed_assumption: str) -> list[str]:
        """Invalidate all active forecasts that depend on a failed assumption (Spec 27, 58, 59)."""
        invalidated_ids: list[str] = []
        lowered = failed_assumption.lower()
        for fct in self._forecasts.values():
            if fct.status == ForecastStatus.ACTIVE:
                for a in fct.assumptions:
                    if lowered in a.lower() or any(w in a.lower() for w in lowered.split()):
                        fct.status = ForecastStatus.INVALIDATED
                        invalidated_ids.append(fct.forecast_id)
                        logger.warning(
                            "FORECAST_INVALIDATED: id=%s assumption_failed='%s'",
                            fct.forecast_id,
                            failed_assumption,
                        )
                        break
        return invalidated_ids

    def get_forecast(self, forecast_id: str) -> ForecastRecord | None:
        """Retrieve forecast by ID."""
        return self._forecasts.get(forecast_id)

    def list_forecasts(
        self,
        status: ForecastStatus | None = None,
        horizon: ForesightHorizon | None = None,
        tenant_id: str = "default",
    ) -> list[ForecastRecord]:
        """List forecasts matching criteria."""
        results: list[ForecastRecord] = []
        for f in self._forecasts.values():
            if tenant_id != "default" and f.tenant_id != tenant_id:
                continue
            if status and f.status != status:
                continue
            if horizon and f.horizon != horizon:
                continue
            results.append(f)
        return results

    def clear(self) -> None:
        """Clear forecasts cache (for tests)."""
        self._forecasts.clear()


long_horizon_forecaster = LongHorizonForecaster()
