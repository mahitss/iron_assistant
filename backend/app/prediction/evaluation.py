"""Forecast Evaluation Metrics and Baseline Comparison (Task 74, Spec 13, 68).

Computes:
- Point metrics: MAE, RMSE, sMAPE, directional accuracy
- Interval metrics: empirical coverage, interval width, coverage calibration error
- Probabilistic metrics: Brier score, log loss
- Baseline comparison: Mean Squared Skill Score (MSSS), outperformance check
- Warning metrics: precision, recall, false positive rate, lead-time stats
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple


class ForecastEvaluator:
    """Computes semantically valid statistical evaluation metrics for forecasts and early warnings."""

    @staticmethod
    def evaluate_point_metrics(
        actuals: List[float],
        predictions: List[float],
        prev_actuals: Optional[List[float]] = None,
    ) -> Dict[str, float]:
        """Compute point forecast accuracy metrics (MAE, RMSE, sMAPE, Directional)."""
        if not actuals or not predictions or len(actuals) != len(predictions):
            return {"mae": 0.0, "rmse": 0.0, "smape": 0.0, "directional_accuracy": 0.0, "sample_size": 0}

        n = len(actuals)
        errors = [actuals[i] - predictions[i] for i in range(n)]
        mae = sum(abs(e) for e in errors) / n
        mse = sum(e ** 2 for e in errors) / n
        rmse = math.sqrt(mse)

        # sMAPE: safe against near-zero denominators
        smape_sum = 0.0
        for i in range(n):
            denom = abs(actuals[i]) + abs(predictions[i])
            if denom > 1e-9:
                smape_sum += (2.0 * abs(actuals[i] - predictions[i])) / denom
        smape = (smape_sum / n) * 100.0

        # Directional accuracy
        directional_acc = 0.0
        if prev_actuals and len(prev_actuals) == n:
            correct_dir = 0
            for i in range(n):
                act_diff = actuals[i] - prev_actuals[i]
                pred_diff = predictions[i] - prev_actuals[i]
                if (act_diff >= 0 and pred_diff >= 0) or (act_diff < 0 and pred_diff < 0):
                    correct_dir += 1
            directional_acc = correct_dir / n

        return {
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "smape": round(smape, 4),
            "directional_accuracy": round(directional_acc, 4),
            "sample_size": n,
        }

    @staticmethod
    def evaluate_interval_metrics(
        actuals: List[float],
        lower_bounds: List[float],
        upper_bounds: List[float],
        coverage_target: float = 0.90,
    ) -> Dict[str, float]:
        """Compute coverage percentage, mean width, and coverage calibration error."""
        if not actuals or len(actuals) != len(lower_bounds) or len(actuals) != len(upper_bounds):
            return {"coverage_rate": 0.0, "mean_interval_width": 0.0, "coverage_error": 0.0, "sample_size": 0}

        n = len(actuals)
        hits = 0
        widths: List[float] = []

        for i in range(n):
            if lower_bounds[i] <= actuals[i] <= upper_bounds[i]:
                hits += 1
            widths.append(upper_bounds[i] - lower_bounds[i])

        coverage = hits / n
        mean_width = sum(widths) / n
        coverage_error = abs(coverage - coverage_target)

        return {
            "coverage_rate": round(coverage, 4),
            "mean_interval_width": round(mean_width, 4),
            "coverage_error": round(coverage_error, 4),
            "coverage_target": coverage_target,
            "sample_size": n,
        }

    @staticmethod
    def evaluate_probabilistic_metrics(
        actual_occurred: List[int],  # 0 or 1
        predicted_probs: List[float],  # 0.0 to 1.0
    ) -> Dict[str, float]:
        """Compute Brier score and binary cross-entropy log loss."""
        if not actual_occurred or len(actual_occurred) != len(predicted_probs):
            return {"brier_score": 0.25, "log_loss": 0.693, "sample_size": 0}

        n = len(actual_occurred)
        brier_sum = sum((predicted_probs[i] - actual_occurred[i]) ** 2 for i in range(n))
        brier_score = brier_sum / n

        eps = 1e-15
        log_loss_sum = 0.0
        for i in range(n):
            y = actual_occurred[i]
            p = max(eps, min(1.0 - eps, predicted_probs[i]))
            log_loss_sum += -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))
        log_loss = log_loss_sum / n

        return {
            "brier_score": round(brier_score, 4),
            "log_loss": round(log_loss, 4),
            "sample_size": n,
        }

    @staticmethod
    def compare_with_baseline(
        model_predictions: List[float],
        baseline_predictions: List[float],
        actuals: List[float],
    ) -> Dict[str, Any]:
        """Calculates Mean Squared Skill Score: MSSS = 1 - (MSE_model / MSE_baseline) (Spec 9)."""
        if not actuals or len(actuals) != len(model_predictions) or len(actuals) != len(baseline_predictions):
            return {"skill_score_msss": 0.0, "outperformed_baseline": False}

        n = len(actuals)
        mse_model = sum((actuals[i] - model_predictions[i]) ** 2 for i in range(n)) / n
        mse_baseline = sum((actuals[i] - baseline_predictions[i]) ** 2 for i in range(n)) / n

        if mse_baseline < 1e-9:
            skill_score = 0.0 if mse_model < 1e-9 else -1.0
        else:
            skill_score = 1.0 - (mse_model / mse_baseline)

        outperformed = mse_model < mse_baseline

        return {
            "mse_model": round(mse_model, 4),
            "mse_baseline": round(mse_baseline, 4),
            "skill_score_msss": round(skill_score, 4),
            "outperformed_baseline": outperformed,
        }

    @staticmethod
    def evaluate_early_warning_metrics(
        warning_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute precision, recall, false-positive rate, and lead time stats (Spec 68)."""
        tp = 0
        fp = 0
        fn = 0
        lead_times: List[float] = []

        for rec in warning_records:
            resolution = rec.get("resolution")
            was_warning = rec.get("warned", True)
            event_occurred = rec.get("event_occurred", False)

            if was_warning and event_occurred:
                tp += 1
                lt = rec.get("lead_time_seconds")
                if lt is not None and lt >= 0:
                    lead_times.append(float(lt))
            elif was_warning and not event_occurred:
                fp += 1
            elif not was_warning and event_occurred:
                fn += 1

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        fp_rate = (fp / (tp + fp)) if (tp + fp) > 0 else 0.0

        mean_lead_time = (sum(lead_times) / len(lead_times)) if lead_times else 0.0
        min_lead_time = min(lead_times) if lead_times else 0.0
        max_lead_time = max(lead_times) if lead_times else 0.0

        return {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "false_positive_rate": round(fp_rate, 4),
            "mean_lead_time_seconds": round(mean_lead_time, 1),
            "min_lead_time_seconds": round(min_lead_time, 1),
            "max_lead_time_seconds": round(max_lead_time, 1),
        }


def evaluate_point_forecast(
    predictions: List[float],
    actuals: List[float],
    previous: Optional[List[float]] = None,
) -> Dict[str, Any]:
    res = ForecastEvaluator.evaluate_point_metrics(
        actuals=actuals,
        predictions=predictions,
        prev_actuals=previous,
    )
    res["count"] = res.get("sample_size", len(predictions))
    return res


def evaluate_interval_forecast(
    intervals: List[Any],
    actuals: List[float],
) -> Dict[str, Any]:
    lowers = [it.lower if hasattr(it, "lower") else it[0] for it in intervals]
    uppers = [it.upper if hasattr(it, "upper") else it[1] for it in intervals]
    coverage_target = intervals[0].coverage_target if intervals and hasattr(intervals[0], "coverage_target") else 0.90
    res = ForecastEvaluator.evaluate_interval_metrics(
        actuals=actuals,
        lower_bounds=lowers,
        upper_bounds=uppers,
        coverage_target=coverage_target,
    )
    res["count"] = res.get("sample_size", len(actuals))
    return res


def evaluate_probabilistic_forecast(
    probs: List[float],
    outcomes: List[int],
) -> Dict[str, Any]:
    res = ForecastEvaluator.evaluate_probabilistic_metrics(
        actual_occurred=outcomes,
        predicted_probs=probs,
    )
    res["count"] = res.get("sample_size", len(probs))
    return res


def compare_against_baseline(
    model_errors: Optional[List[float]] = None,
    baseline_errors: Optional[List[float]] = None,
    model_predictions: Optional[List[float]] = None,
    baseline_predictions: Optional[List[float]] = None,
    actuals: Optional[List[float]] = None,
) -> Dict[str, Any]:
    if model_errors is not None and baseline_errors is not None:
        n = len(model_errors)
        mse_m = sum(e ** 2 for e in model_errors) / n if n else 0.0
        mse_b = sum(e ** 2 for e in baseline_errors) / n if n else 0.0
        msss = 1.0 - (mse_m / mse_b) if mse_b > 1e-9 else 0.0
        return {
            "model_mse": round(mse_m, 4),
            "baseline_mse": round(mse_b, 4),
            "msss": round(msss, 4),
            "outperformed_baseline": mse_m < mse_b,
        }
    if actuals and model_predictions and baseline_predictions:
        return ForecastEvaluator.compare_with_baseline(
            model_predictions=model_predictions,
            baseline_predictions=baseline_predictions,
            actuals=actuals,
        )
    return {"msss": 0.0, "outperformed_baseline": False}


def evaluate_early_warning(
    warnings: List[Dict[str, Any]],
    outcomes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    outcome_map = {o["warning_id"]: o.get("confirmed", False) for o in outcomes}
    records = []
    for w in warnings:
        wid = w["warning_id"]
        confirmed = outcome_map.get(wid, False)
        records.append({
            "warning_id": wid,
            "warned": True,
            "event_occurred": confirmed,
            "lead_time_seconds": w.get("lead_time_seconds"),
        })
    warning_ids = {w["warning_id"] for w in warnings}
    for o in outcomes:
        if o["warning_id"] not in warning_ids and o.get("confirmed", False):
            records.append({
                "warning_id": o["warning_id"],
                "warned": False,
                "event_occurred": True,
            })
    eval_stats = ForecastEvaluator.evaluate_early_warning_metrics(records)
    return {
        "warnings_count": len(warnings),
        "confirmed_count": eval_stats["true_positives"],
        "precision": eval_stats["precision"],
        "recall": eval_stats["recall"],
        "false_positive_rate": eval_stats["false_positive_rate"],
        "lead_time_stats": {
            "mean_lead_time_seconds": eval_stats["mean_lead_time_seconds"],
            "min_lead_time_seconds": eval_stats["min_lead_time_seconds"],
            "max_lead_time_seconds": eval_stats["max_lead_time_seconds"],
        },
    }
