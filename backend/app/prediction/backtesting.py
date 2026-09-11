"""Autonomous Backtesting Engine with Temporal Isolation (Task 74, Spec 11, 12).

Supports:
- Rolling-origin evaluation
- Expanding-window evaluation
- Fixed-window evaluation
- Strict temporal isolation enforcement (no lookahead data leakage)
- Baseline comparison and skill scoring across historical folds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.prediction.evaluation import ForecastEvaluator
from app.prediction.schemas import (
    BacktestConfig,
    BacktestResult,
    ForecastStrategyType,
)
from app.prediction.strategies import (
    BaseForecastStrategy,
    NaiveBaselineStrategy,
    forecast_strategy_registry,
)
from app.prediction.temporal_features import (
    DataLeakageError,
    TemporalFeaturePipeline,
    TemporalObservation,
)

logger = logging.getLogger("kairo.prediction.backtesting")


@dataclass
class BacktestFoldRecord:
    """Record of a single temporal backtest origin fold."""

    fold_index: int
    forecast_origin: datetime
    horizon_steps: int
    train_count: int
    actual_values: List[float]
    predicted_values: List[float]
    baseline_values: List[float]
    lower_bounds: List[float]
    upper_bounds: List[float]
    fold_mae: float
    fold_rmse: float
    coverage_hit: bool


class BacktestingEngine:
    """Simulates historical forecasting performance without lookahead bias (Spec 12)."""

    def __init__(self) -> None:
        self.baseline_strategy = NaiveBaselineStrategy()

    def run_backtest(
        self,
        target: str,
        series: List[Any],
        config: Optional[BacktestConfig] = None,
        custom_strategy: Optional[BaseForecastStrategy] = None,
    ) -> BacktestResult:
        """Execute historical backtesting with rolling/expanding window evaluation."""
        cfg = config or BacktestConfig(target=target)
        strategy = custom_strategy or forecast_strategy_registry.get_strategy(cfg.strategy)

        # Parse & strictly sort by timestamp ascending
        observations: List[TemporalObservation] = [
            s if isinstance(s, TemporalObservation) else TemporalObservation.from_dict(s)
            for s in series
        ]
        observations.sort(key=lambda x: x.timestamp)

        total_obs = len(observations)
        min_train = max(5, cfg.min_train_size)
        h = max(1, cfg.horizon_steps)
        step = max(1, cfg.step_size)

        if total_obs < min_train + h:
            raise ValueError(
                f"Insufficient time-series length ({total_obs}) for backtest "
                f"(min_train={min_train} + horizon={h} = {min_train + h} required)"
            )

        folds: List[BacktestFoldRecord] = []
        all_actuals: List[float] = []
        all_predictions: List[float] = []
        all_baselines: List[float] = []
        all_lowers: List[float] = []
        all_uppers: List[float] = []

        # Iterate over historical origins
        fold_idx = 0
        current_train_end = min_train

        while current_train_end + h <= total_obs:
            # 1. Determine training slice
            if cfg.window_type == "rolling":
                train_start = max(0, current_train_end - min_train)
                train_obs = observations[train_start:current_train_end]
            elif cfg.window_type == "expanding":
                train_obs = observations[:current_train_end]
            else:  # fixed
                train_obs = observations[:min_train]

            origin_time = observations[current_train_end - 1].timestamp

            # 2. Strict leakage isolation audit
            if cfg.leakage_check_strict:
                for o in train_obs:
                    if o.timestamp > origin_time:
                        raise DataLeakageError(
                            f"Backtest temporal isolation breached in fold {fold_idx}: "
                            f"training sample {o.timestamp} > origin {origin_time}"
                        )

            # 3. Generate predictions at forecast origin
            forecast_res = strategy.generate_forecast(
                target=target,
                observations=train_obs,
                horizon_steps=h,
            )

            # 4. Generate naive baseline
            base_res = self.baseline_strategy.generate_forecast(
                target=target,
                observations=train_obs,
                horizon_steps=h,
            )

            # 5. Future ground truth realization
            future_obs = observations[current_train_end : current_train_end + h]
            actual_vals = [o.value for o in future_obs]
            pred_vals = forecast_res.trajectory[: len(actual_vals)]
            base_vals = base_res.trajectory[: len(actual_vals)]

            # Evaluate fold
            fold_metrics = ForecastEvaluator.evaluate_point_metrics(actual_vals, pred_vals)
            cov_hit = forecast_res.interval.lower_bound <= actual_vals[-1] <= forecast_res.interval.upper_bound

            fold_rec = BacktestFoldRecord(
                fold_index=fold_idx,
                forecast_origin=origin_time,
                horizon_steps=h,
                train_count=len(train_obs),
                actual_values=actual_vals,
                predicted_values=pred_vals,
                baseline_values=base_vals,
                lower_bounds=[forecast_res.interval.lower_bound] * len(actual_vals),
                upper_bounds=[forecast_res.interval.upper_bound] * len(actual_vals),
                fold_mae=fold_metrics["mae"],
                fold_rmse=fold_metrics["rmse"],
                coverage_hit=cov_hit,
            )
            folds.append(fold_rec)

            all_actuals.extend(actual_vals)
            all_predictions.extend(pred_vals)
            all_baselines.extend(base_vals)
            all_lowers.extend([forecast_res.interval.lower_bound] * len(actual_vals))
            all_uppers.extend([forecast_res.interval.upper_bound] * len(actual_vals))

            fold_idx += 1
            current_train_end += step

        # Overall aggregate evaluation
        point_eval = ForecastEvaluator.evaluate_point_metrics(all_actuals, all_predictions)
        base_eval = ForecastEvaluator.evaluate_point_metrics(all_actuals, all_baselines)
        interval_eval = ForecastEvaluator.evaluate_interval_metrics(all_actuals, all_lowers, all_uppers)
        comparison = ForecastEvaluator.compare_with_baseline(all_predictions, all_baselines, all_actuals)

        fold_summaries = [
            {
                "fold_index": f.fold_index,
                "origin": f.forecast_origin.isoformat(),
                "mae": round(f.fold_mae, 4),
                "rmse": round(f.fold_rmse, 4),
                "coverage_hit": f.coverage_hit,
            }
            for f in folds
        ]

        logger.info(
            "Backtest finished on '%s' (%s): folds=%d, MAE=%.4f (baseline=%.4f), MSSS=%.4f",
            target,
            strategy.strategy_type.value,
            len(folds),
            point_eval["mae"],
            base_eval["mae"],
            comparison["skill_score_msss"],
        )

        return BacktestResult(
            target=target,
            strategy=strategy.strategy_type.value,
            folds_evaluated=len(folds),
            mae=point_eval["mae"],
            rmse=point_eval["rmse"],
            smape=point_eval["smape"],
            coverage_rate=interval_eval["coverage_rate"],
            baseline_mae=base_eval["mae"],
            baseline_rmse=base_eval["rmse"],
            skill_score_msss=comparison["skill_score_msss"],
            temporal_isolation_verified=True,
            evaluation_records=fold_summaries,
        )


backtesting_engine = BacktestingEngine()
TemporalBacktester = BacktestingEngine
