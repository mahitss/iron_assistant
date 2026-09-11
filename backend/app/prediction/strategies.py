"""Forecasting Strategy Layer and Deterministic Baselines (Task 74, Spec 8, 9, 16, 17, 18).

Provides:
- Abstract strategy protocol with capability introspection
- Deterministic statistical baselines (Naive, Moving Average, Exponential Smoothing, Trend Extrapolation, Seasonal)
- Causal and World Model integration strategies
- Multi-model ensemble with explicit disagreement detection
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional

from app.prediction.schemas import (
    ForecastHorizon,
    ForecastStrategyType,
    PredictionInterval,
    UncertaintyBreakdown,
)
from app.prediction.temporal_features import TemporalFeaturePipeline, TemporalObservation


@dataclass
class ForecastStrategyResult:
    """Standardized output from any forecasting strategy."""

    strategy_type: ForecastStrategyType
    target: str
    point_estimate: float
    interval: PredictionInterval
    trajectory: List[float]
    assumptions: List[str]
    uncertainty: UncertaintyBreakdown
    model_name: str
    competing_forecasts: Dict[str, float] = field(default_factory=dict)
    disagreement_detected: bool = False
    disagreement_spread: float = 0.0
    strategy_metadata: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        if item == "predicted_value":
            return self.point_estimate
        if item == "baseline_value":
            return self.strategy_metadata.get("baseline_value", self.point_estimate)
        if item == "prediction_interval":
            return self.interval.model_dump() if hasattr(self.interval, "model_dump") else self.interval
        if item == "strategy":
            return self.strategy_type.value
        if item == "metadata":
            meta = dict(self.strategy_metadata)
            meta["sub_predictions"] = self.competing_forecasts
            meta["disagreement_spread"] = self.disagreement_spread
            meta["high_disagreement"] = self.disagreement_detected
            return meta
        if item == "uncertainty":
            return self.uncertainty.model_dump() if hasattr(self.uncertainty, "model_dump") else self.uncertainty
        if hasattr(self, item):
            return getattr(self, item)
        return self.strategy_metadata.get(item)

    def __contains__(self, item: str) -> bool:
        if item in ("predicted_value", "baseline_value", "prediction_interval", "strategy", "metadata", "uncertainty"):
            return True
        return hasattr(self, item) or (item in self.strategy_metadata)


class BaseForecastStrategy(ABC):
    """Abstract base class for deterministic and model-based forecast strategies."""

    strategy_type: ForecastStrategyType

    @staticmethod
    def _normalize_observations(observations: Any, history: Any = None) -> List[TemporalObservation]:
        obs = observations if observations is not None else (history or [])
        clean: List[TemporalObservation] = []
        for item in obs:
            if isinstance(item, TemporalObservation):
                clean.append(item)
            elif isinstance(item, (int, float)):
                clean.append(TemporalObservation(timestamp=datetime.now(timezone.utc), value=float(item)))
            elif isinstance(item, dict):
                clean.append(TemporalObservation.from_dict(item))
        return clean

    @abstractmethod
    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        """Generate point, interval, and trajectory forecast."""


class NaiveBaselineStrategy(BaseForecastStrategy):
    """Predicts future value equals the last observed value: y_{t+h} = y_t (Spec 9)."""

    strategy_type = ForecastStrategyType.NAIVE_BASELINE

    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        obs = self._normalize_observations(observations, history)
        observations = obs
        if not observations:
            latest = 0.0
            spread = 1.0
        else:
            latest = observations[-1].value
            values = [o.value for o in observations]
            if len(values) > 1:
                mean_val = sum(values) / len(values)
                variance = sum((x - mean_val) ** 2 for x in values) / (len(values) - 1)
                spread = max(0.5, math.sqrt(variance) * 1.645)  # ~90% confidence under normality
            else:
                spread = max(1.0, abs(latest) * 0.15)

        # Horizon expands uncertainty
        expanded_spread = spread * (1.0 + (horizon_steps * 0.05))
        lower = round(latest - expanded_spread, 4)
        upper = round(latest + expanded_spread, 4)

        interval = PredictionInterval(
            lower_bound=lower,
            point_estimate=round(latest, 4),
            upper_bound=upper,
            coverage_target=coverage_target,
            unit=unit,
        )

        trajectory = [round(latest, 4) for _ in range(horizon_steps)]

        uncertainty = UncertaintyBreakdown(
            model_uncertainty=0.15,
            data_uncertainty=0.10,
            parameter_uncertainty=0.05,
            environmental_uncertainty=0.20,
            scenario_spread=0.0,
            qualitative_rationale="Naive persistent baseline assuming current value continues",
            composite_uncertainty=0.25,
        )

        return ForecastStrategyResult(
            strategy_type=self.strategy_type,
            target=target,
            point_estimate=round(latest, 4),
            interval=interval,
            trajectory=trajectory,
            assumptions=["Future values remain stable around last verified observation"],
            uncertainty=uncertainty,
            model_name="deterministic_naive_baseline",
            strategy_metadata={"last_observed_value": latest, "sample_size": len(observations)},
        )


class MovingAverageStrategy(BaseForecastStrategy):
    """Predicts future value equals the rolling mean over window w (Spec 8)."""

    strategy_type = ForecastStrategyType.MOVING_AVERAGE

    def __init__(self, window_size: int = 5) -> None:
        self.window_size = window_size

    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        obs = self._normalize_observations(observations, history)
        values = [o.value for o in obs] if obs else [0.0]
        w = min(len(values), kwargs.get("window_size", self.window_size))
        slice_vals = values[-w:]
        point_est = sum(slice_vals) / w

        if len(slice_vals) > 1:
            variance = sum((x - point_est) ** 2 for x in slice_vals) / (len(slice_vals) - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = max(1.0, abs(point_est) * 0.15)

        expanded_spread = max(0.5, std_dev * 1.645 * (1.0 + (horizon_steps * 0.08)))
        lower = round(point_est - expanded_spread, 4)
        upper = round(point_est + expanded_spread, 4)

        interval = PredictionInterval(
            lower_bound=lower,
            point_estimate=round(point_est, 4),
            upper_bound=upper,
            coverage_target=coverage_target,
            unit=unit,
        )

        trajectory = [round(point_est, 4) for _ in range(horizon_steps)]

        model_unc = 0.12 if len(values) >= 5 else 0.20
        data_unc = 0.10 if len(values) >= 10 else 0.20

        uncertainty = UncertaintyBreakdown(
            model_uncertainty=model_unc,
            data_uncertainty=data_unc,
            parameter_uncertainty=0.10,
            environmental_uncertainty=0.25,
            scenario_spread=0.0,
            qualitative_rationale=f"Moving average baseline over rolling window of {w} observations",
            composite_uncertainty=round((model_unc + data_unc + 0.35) / 3.0, 3),
        )

        return ForecastStrategyResult(
            strategy_type=self.strategy_type,
            target=target,
            point_estimate=round(point_est, 4),
            interval=interval,
            trajectory=trajectory,
            assumptions=[f"Process revolves around {w}-period rolling central tendency"],
            uncertainty=uncertainty,
            model_name=f"moving_average_w{w}",
            strategy_metadata={"window_size": w, "std_dev": std_dev},
        )


class ExponentialSmoothingStrategy(BaseForecastStrategy):
    """Holt's linear exponential smoothing capturing level and trend (Spec 8)."""

    strategy_type = ForecastStrategyType.EXPONENTIAL_SMOOTHING

    def __init__(self, alpha: float = 0.3, beta: float = 0.1) -> None:
        self.alpha = alpha
        self.beta = beta

    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        obs = self._normalize_observations(observations, history)
        values = [o.value for o in obs] if obs else [0.0]
        alpha = kwargs.get("alpha", self.alpha)
        beta = kwargs.get("beta", self.beta)

        if len(values) < 2:
            level = values[0]
            trend = 0.0
        else:
            level = values[0]
            trend = values[1] - values[0]
            for val in values[1:]:
                prev_level = level
                level = alpha * val + (1 - alpha) * (level + trend)
                trend = beta * (level - prev_level) + (1 - beta) * trend

        trajectory: List[float] = []
        for h in range(1, horizon_steps + 1):
            trajectory.append(round(level + h * trend, 4))

        final_point = trajectory[-1] if trajectory else round(level, 4)

        # Spread grows with horizon
        volatility = abs(trend) * 2.0 + max(1.0, abs(level) * 0.1)
        spread = volatility * 1.645 * math.sqrt(horizon_steps)
        lower = round(final_point - spread, 4)
        upper = round(final_point + spread, 4)

        interval = PredictionInterval(
            lower_bound=lower,
            point_estimate=final_point,
            upper_bound=upper,
            coverage_target=coverage_target,
            unit=unit,
        )

        uncertainty = UncertaintyBreakdown(
            model_uncertainty=0.18,
            data_uncertainty=0.12,
            parameter_uncertainty=0.10,
            environmental_uncertainty=0.22,
            scenario_spread=0.0,
            qualitative_rationale=f"Double exponential smoothing with alpha={alpha:.2f}, beta={beta:.2f}",
            composite_uncertainty=0.26,
        )

        return ForecastStrategyResult(
            strategy_type=self.strategy_type,
            target=target,
            point_estimate=final_point,
            interval=interval,
            trajectory=trajectory,
            assumptions=["Level and trend dynamics continue without abrupt regime breaks"],
            uncertainty=uncertainty,
            model_name="holt_exponential_smoothing",
            strategy_metadata={"alpha": alpha, "beta": beta, "final_level": level, "final_trend": trend, "slope": trend},
        )


class TrendExtrapolationStrategy(BaseForecastStrategy):
    """Ordinary least squares linear trend projection (Spec 8)."""

    strategy_type = ForecastStrategyType.TREND_EXTRAPOLATION

    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        obs = self._normalize_observations(observations, history)
        values = [o.value for o in obs] if obs else [0.0]
        n = len(values)

        if n < 2:
            slope = 0.0
            intercept = values[0]
            residuals_std = 1.0
        else:
            w = min(n, kwargs.get("lookback", 15))
            y_vals = values[-w:]
            x_vals = list(range(w))
            x_bar = sum(x_vals) / w
            y_bar = sum(y_vals) / w
            num = sum((x_vals[i] - x_bar) * (y_vals[i] - y_bar) for i in range(w))
            den = sum((x_vals[i] - x_bar) ** 2 for i in range(w))
            slope = (num / den) if den != 0 else 0.0
            intercept = y_bar - slope * x_bar

            # Residual standard error
            fitted = [intercept + slope * i for i in range(w)]
            sse = sum((y_vals[i] - fitted[i]) ** 2 for i in range(w))
            residuals_std = math.sqrt(sse / max(1, w - 2)) if w > 2 else max(1.0, abs(y_bar) * 0.1)

        trajectory: List[float] = []
        last_x = (min(n, kwargs.get("lookback", 15)) - 1) if n >= 2 else 0
        for h in range(1, horizon_steps + 1):
            future_x = last_x + h
            trajectory.append(round(intercept + slope * future_x, 4))

        point_est = trajectory[-1] if trajectory else round(intercept, 4)
        spread = max(0.5, residuals_std * 1.645 * (1.0 + (horizon_steps * 0.1)))
        lower = round(point_est - spread, 4)
        upper = round(point_est + spread, 4)

        interval = PredictionInterval(
            lower_bound=lower,
            point_estimate=point_est,
            upper_bound=upper,
            coverage_target=coverage_target,
            unit=unit,
        )

        data_unc = 0.60 if n < 2 else (0.30 if n < 5 else 0.15)
        model_unc = 0.35 if n < 2 else 0.20

        uncertainty = UncertaintyBreakdown(
            model_uncertainty=model_unc,
            data_uncertainty=data_unc,
            parameter_uncertainty=0.12,
            environmental_uncertainty=0.25,
            scenario_spread=0.0,
            qualitative_rationale=f"OLS trend extrapolation over {min(n, 15)} samples with slope={slope:.4f}",
            composite_uncertainty=round((model_unc + data_unc + 0.37) / 3.0, 3),
        )

        return ForecastStrategyResult(
            strategy_type=self.strategy_type,
            target=target,
            point_estimate=point_est,
            interval=interval,
            trajectory=trajectory,
            assumptions=["Recent velocity and trajectory persist linearly into near future"],
            uncertainty=uncertainty,
            model_name="ols_trend_extrapolation",
            strategy_metadata={"slope": slope, "intercept": intercept, "residuals_std": residuals_std},
        )


class HistoricalSeasonalStrategy(BaseForecastStrategy):
    """Matches periodic cycle phases from past intervals (Spec 8)."""

    strategy_type = ForecastStrategyType.HISTORICAL_SEASONAL

    def __init__(
        self,
        period_length: int = 7,
        seasonality_period: Optional[int] = None,
        season_length: Optional[int] = None,
    ) -> None:
        self.period_length = seasonality_period or season_length or period_length
        self.seasonality_period = self.period_length
        self.season_length = self.period_length

    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        obs = self._normalize_observations(observations, history)
        values = [o.value for o in obs] if obs else [0.0]
        period = kwargs.get("period", self.period_length)
        n = len(values)

        trajectory: List[float] = []
        for h in range(horizon_steps):
            idx = (n + h) % period
            if n >= period:
                # Average corresponding phase across completed cycles
                phase_vals = [values[i] for i in range(idx, n, period)]
                val = sum(phase_vals) / len(phase_vals)
            else:
                val = values[idx % n]
            trajectory.append(round(val, 4))

        point_est = trajectory[-1] if trajectory else values[-1]
        overall_mean = sum(values) / n
        spread = max(1.0, abs(point_est - overall_mean) + 0.5) * 1.645

        interval = PredictionInterval(
            lower_bound=round(point_est - spread, 4),
            point_estimate=point_est,
            upper_bound=round(point_est + spread, 4),
            coverage_target=coverage_target,
            unit=unit,
        )

        uncertainty = UncertaintyBreakdown(
            model_uncertainty=0.19,
            data_uncertainty=0.14,
            parameter_uncertainty=0.15,
            environmental_uncertainty=0.20,
            scenario_spread=0.0,
            qualitative_rationale=f"Periodic seasonal baseline across period={period}",
            composite_uncertainty=0.27,
        )

        return ForecastStrategyResult(
            strategy_type=self.strategy_type,
            target=target,
            point_estimate=point_est,
            interval=interval,
            trajectory=trajectory,
            assumptions=[f"Seasonal cyclical pattern recurs with strict periodicity of {period}"],
            uncertainty=uncertainty,
            model_name=f"historical_seasonal_p{period}",
            strategy_metadata={"period": period, "cycle_count": n // period},
        )


class CausalInterventionStrategy(BaseForecastStrategy):
    """Integrates causal graphs and interventions: P(outcome | do(action)) (Spec 8, 18)."""

    strategy_type = ForecastStrategyType.CAUSAL_INTERVENTION

    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        obs = self._normalize_observations(observations, history)
        values = [o.value for o in obs] if obs else [0.0]
        base_val = values[-1]

        intervention = kwargs.get("intervention")
        causal_effect = float(kwargs.get("causal_effect", 0.0))
        is_observational = intervention is None

        if is_observational:
            point_est = round(base_val, 4)
            assumptions = ["Observational projection without external intervention"]
        else:
            point_est = round(base_val + causal_effect, 4)
            assumptions = [f"Intervention '{intervention}' induces estimated effect delta {causal_effect:+.2f}"]

        spread = max(1.0, abs(point_est) * 0.20)
        interval = PredictionInterval(
            lower_bound=round(point_est - spread, 4),
            point_estimate=point_est,
            upper_bound=round(point_est + spread, 4),
            coverage_target=coverage_target,
            unit=unit,
        )

        trajectory = [round(base_val + (causal_effect * min(1.0, (h + 1) / horizon_steps)), 4) for h in range(horizon_steps)]

        uncertainty = UncertaintyBreakdown(
            model_uncertainty=0.20 if not is_observational else 0.30,
            data_uncertainty=0.15,
            parameter_uncertainty=0.18,
            environmental_uncertainty=0.22,
            scenario_spread=abs(causal_effect) * 0.5,
            qualitative_rationale="Causal interventional estimation using graph effect priors",
            composite_uncertainty=0.30,
        )

        return ForecastStrategyResult(
            strategy_type=self.strategy_type,
            target=target,
            point_estimate=point_est,
            interval=interval,
            trajectory=trajectory,
            assumptions=assumptions,
            uncertainty=uncertainty,
            model_name="causal_dag_interventional_forecaster",
            strategy_metadata={
                "is_observational": is_observational,
                "intervention": intervention,
                "causal_effect": causal_effect,
            },
        )


class EnsembleStrategy(BaseForecastStrategy):
    """Combines independent strategies and exposes model disagreement explicitly (Spec 16)."""

    strategy_type = ForecastStrategyType.ENSEMBLE

    def __init__(self, constituent_strategies: Optional[List[BaseForecastStrategy]] = None) -> None:
        self.strategies = constituent_strategies or [
            NaiveBaselineStrategy(),
            MovingAverageStrategy(window_size=5),
            ExponentialSmoothingStrategy(),
            TrendExtrapolationStrategy(),
        ]

    def generate_forecast(
        self,
        target: str = "metric",
        observations: Optional[List[Any]] = None,
        horizon_steps: int = 1,
        coverage_target: float = 0.90,
        unit: str = "",
        history: Optional[List[Any]] = None,
        **kwargs: Any,
    ) -> ForecastStrategyResult:
        obs = self._normalize_observations(observations, history)
        sub_results: List[ForecastStrategyResult] = []
        competing: Dict[str, float] = {}

        for strat in self.strategies:
            res = strat.generate_forecast(
                target=target,
                observations=obs,
                horizon_steps=horizon_steps,
                coverage_target=coverage_target,
                unit=unit,
                **kwargs,
            )
            sub_results.append(res)
            competing[strat.strategy_type.value] = res.point_estimate

        points = list(competing.values())
        min_p, max_p = min(points), max(points)
        median_point = sorted(points)[len(points) // 2]

        mean_point = sum(points) / len(points)
        disagreement_spread = max_p - min_p
        rel_divergence = (disagreement_spread / max(1.0, abs(mean_point))) if mean_point != 0 else 0.0

        disagreement_detected = rel_divergence > 0.25

        # Interval encloses the constituent forecasts plus buffer
        lowers = [r.interval.lower_bound for r in sub_results]
        uppers = [r.interval.upper_bound for r in sub_results]
        lower_bound = min(lowers)
        upper_bound = max(uppers)

        interval = PredictionInterval(
            lower_bound=round(lower_bound, 4),
            point_estimate=round(median_point, 4),
            upper_bound=round(upper_bound, 4),
            coverage_target=coverage_target,
            unit=unit,
        )

        # Average trajectories
        trajectory: List[float] = []
        for step_idx in range(horizon_steps):
            step_vals = [r.trajectory[step_idx] for r in sub_results if len(r.trajectory) > step_idx]
            trajectory.append(round(sum(step_vals) / len(step_vals), 4) if step_vals else round(median_point, 4))

        uncertainty = UncertaintyBreakdown(
            model_uncertainty=min(1.0, 0.15 + (rel_divergence * 0.5)),
            data_uncertainty=0.12,
            parameter_uncertainty=0.10,
            environmental_uncertainty=0.20,
            scenario_spread=round(rel_divergence, 4),
            qualitative_rationale=(
                f"Ensemble across {len(self.strategies)} models. "
                f"{'High disagreement detected among models.' if disagreement_detected else 'Consensus across constituent strategies.'}"
            ),
            composite_uncertainty=min(0.95, round(0.20 + (rel_divergence * 0.4), 4)),
        )

        assumptions = [f"Synthesizes {len(self.strategies)} distinct algorithmic perspectives"]
        if disagreement_detected:
            assumptions.append(f"Model spread is significant ({disagreement_spread:.2f} {unit}); uncertainty is elevated")

        return ForecastStrategyResult(
            strategy_type=self.strategy_type,
            target=target,
            point_estimate=round(median_point, 4),
            interval=interval,
            trajectory=trajectory,
            assumptions=assumptions,
            uncertainty=uncertainty,
            model_name="multi_strategy_ensemble",
            competing_forecasts=competing,
            disagreement_detected=disagreement_detected,
            disagreement_spread=round(disagreement_spread, 4),
            strategy_metadata={"models_evaluated": len(self.strategies), "divergence_ratio": round(rel_divergence, 4)},
        )


class ForecastStrategyRegistry:
    """Registry providing strategy instantiation and selection (Spec 8, 40)."""

    def __init__(self) -> None:
        self._strategies: Dict[ForecastStrategyType, BaseForecastStrategy] = {
            ForecastStrategyType.NAIVE_BASELINE: NaiveBaselineStrategy(),
            ForecastStrategyType.MOVING_AVERAGE: MovingAverageStrategy(),
            ForecastStrategyType.EXPONENTIAL_SMOOTHING: ExponentialSmoothingStrategy(),
            ForecastStrategyType.TREND_EXTRAPOLATION: TrendExtrapolationStrategy(),
            ForecastStrategyType.HISTORICAL_SEASONAL: HistoricalSeasonalStrategy(),
            ForecastStrategyType.CAUSAL: CausalInterventionStrategy(),
            ForecastStrategyType.ENSEMBLE: EnsembleStrategy(),
        }

    def get_strategy(self, strategy_type: ForecastStrategyType) -> BaseForecastStrategy:
        strat = self._strategies.get(strategy_type)
        if not strat:
            return self._strategies[ForecastStrategyType.TREND_EXTRAPOLATION]
        return strat

    def select_strategy_for_horizon(
        self,
        horizon: ForecastHorizon,
        has_causal_context: bool = False,
    ) -> BaseForecastStrategy:
        """Selects strategy aligned with horizon difficulty and context (Spec 42)."""
        if has_causal_context:
            return self.get_strategy(ForecastStrategyType.CAUSAL)
        if horizon == ForecastHorizon.SHORT:
            return self.get_strategy(ForecastStrategyType.TREND_EXTRAPOLATION)
        if horizon == ForecastHorizon.MEDIUM:
            return self.get_strategy(ForecastStrategyType.EXPONENTIAL_SMOOTHING)
        return self.get_strategy(ForecastStrategyType.ENSEMBLE)


forecast_strategy_registry = ForecastStrategyRegistry()
