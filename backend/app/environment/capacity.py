"""Capacity Modeling, Predictive Forecasting, and Threshold Alerts (Task 54, Prompts #145-#151)."""

from __future__ import annotations

from typing import Any

from app.environment.temporal import utc_now


class CapacityManager:
    """Monitors resource capacity metrics, evaluates thresholds, and distinguishes predictions."""

    DEFAULT_THRESHOLDS = {
        "cpu_pct": 85.0,
        "memory_pct": 85.0,
        "storage_pct": 90.0,
        "connections_pct": 80.0,
        "queue_depth": 10000,
    }

    @staticmethod
    def evaluate_capacity_metrics(
        resource_id: str,
        observed_metrics: dict[str, float | int],
        custom_thresholds: dict[str, float | int] | None = None,
    ) -> dict[str, Any]:
        """Evaluates observed capacity against thresholds, generating alerts if crossed."""
        thresholds = {**CapacityManager.DEFAULT_THRESHOLDS, **(custom_thresholds or {})}
        alerts = []

        for metric, val in observed_metrics.items():
            thresh = thresholds.get(metric)
            if thresh is not None and val >= thresh:
                alerts.append({
                    "metric": metric,
                    "observed": val,
                    "threshold": thresh,
                    "severity": "CRITICAL" if val >= thresh * 1.15 else "WARNING",
                    "timestamp": utc_now().isoformat(),
                })

        return {
            "resource_id": resource_id,
            "metrics": observed_metrics,
            "thresholds": thresholds,
            "is_saturated": len(alerts) > 0,
            "alerts": alerts,
            "evaluated_at": utc_now().isoformat(),
        }

    @staticmethod
    def forecast_capacity(
        resource_id: str,
        current_val: float,
        growth_rate_per_hour: float,
        horizon_hours: int = 24,
    ) -> dict[str, Any]:
        """Prompt #146, #147: Clearly distinguish predictions from observations."""
        predicted_val = round(current_val + (growth_rate_per_hour * horizon_hours), 2)
        return {
            "resource_id": resource_id,
            "forecast_type": "PREDICTION",
            "is_prediction": True,  # Prompt #147: clearly distinguish predictions
            "horizon_hours": horizon_hours,
            "current_observed": current_val,
            "predicted_value": predicted_val,
            "confidence": 0.85,
            "generated_at": utc_now().isoformat(),
        }
