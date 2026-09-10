"""Signal baseline engine, incremental calibration, and anti-poisoning defenses (Task 60)."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from app.situational_awareness.safety import protect_baseline_from_incident
from app.situational_awareness.schemas import SignalBaseline

logger = logging.getLogger(__name__)


class BaselineEngine:
    """Maintains statistical operational baselines, versioning, and anti-poisoning quarantines."""

    def __init__(self) -> None:
        self._baselines: dict[str, SignalBaseline] = {}

    def get_key(self, signal_name: str, resource: str, environment: str = "development") -> str:
        return f"{signal_name.lower()}::{resource.lower()}::{environment.lower()}"

    def register_baseline(self, baseline: SignalBaseline) -> SignalBaseline:
        key = self.get_key(baseline.signal_name, baseline.resource, baseline.environment)
        self._baselines[key] = baseline
        return baseline

    def get_baseline(
        self,
        signal_name: str,
        resource: str,
        environment: str = "development",
    ) -> SignalBaseline | None:
        key = self.get_key(signal_name, resource, environment)
        return self._baselines.get(key)

    def list_baselines(self, environment: str | None = None) -> list[SignalBaseline]:
        results = list(self._baselines.values())
        if environment:
            results = [b for b in results if b.environment.lower() == environment.lower()]
        return results

    def record_observation(
        self,
        signal_name: str,
        resource: str,
        value: float,
        environment: str = "development",
        is_incident_period: bool = False,
    ) -> SignalBaseline:
        """Update baseline using Welford's algorithm, quarantining abnormal/incident periods."""
        key = self.get_key(signal_name, resource, environment)
        baseline = self._baselines.get(key)

        if not baseline:
            baseline = SignalBaseline(
                signal_name=signal_name,
                resource=resource,
                environment=environment,
                mean_val=float(value),
                std_dev=1.0,
                min_val=float(value),
                max_val=float(value),
                sample_count=1,
            )
            self._baselines[key] = baseline
            return baseline

        # Invariant 21: Protect baseline from incident poisoning
        if not protect_baseline_from_incident(is_incident_period, baseline.is_quarantined):
            logger.warning(
                "BASELINE_POISONING_PREVENTED: Signal '%s' on '%s' ignored due to active incident/quarantine.",
                signal_name,
                resource,
            )
            return baseline

        # Incremental calibration
        n = baseline.sample_count + 1
        old_mean = baseline.mean_val
        new_mean = old_mean + (value - old_mean) / n

        # Approximate variance update
        variance = (baseline.std_dev**2) * (n - 1) + (value - old_mean) * (value - new_mean)
        new_std = math.sqrt(max(0.01, variance / n))

        baseline.sample_count = n
        baseline.mean_val = round(new_mean, 4)
        baseline.std_dev = round(new_std, 4)
        baseline.min_val = min(baseline.min_val, float(value))
        baseline.max_val = max(baseline.max_val, float(value))
        baseline.version += 1
        baseline.last_calibrated_at = datetime.now(timezone.utc)

        return baseline

    def populate_defaults(self) -> None:
        """Initialize standard trusted baselines across core system signals."""
        defaults = [
            ("cpu_usage_percent", "app-server-01", "production", 45.0, 10.0, 5.0, 95.0),
            ("memory_usage_percent", "app-server-01", "production", 60.0, 8.0, 20.0, 90.0),
            ("api_latency_ms", "gateway-api", "production", 35.0, 12.0, 5.0, 300.0),
            ("http_error_rate", "gateway-api", "production", 0.005, 0.002, 0.0, 0.05),
            ("db_query_time_ms", "postgres-primary", "production", 15.0, 5.0, 1.0, 120.0),
            ("cpu_usage_percent", "app-server-01", "development", 25.0, 8.0, 2.0, 80.0),
        ]
        for name, res, env, mean, std, min_v, max_v in defaults:
            self.register_baseline(
                SignalBaseline(
                    signal_name=name,
                    resource=res,
                    environment=env,
                    mean_val=mean,
                    std_dev=std,
                    min_val=min_v,
                    max_val=max_v,
                    sample_count=500,
                )
            )


baseline_engine = BaselineEngine()
baseline_engine.populate_defaults()
