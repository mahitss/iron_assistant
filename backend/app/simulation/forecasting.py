"""Future state forecasting and time-horizon projection."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HorizonProjection(BaseModel):
    """Discrete time-horizon projection frame."""

    horizon_name: str  # SHORT_TERM, MEDIUM_TERM, LONG_TERM
    time_offset_seconds: int
    projected_metrics: dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.8
    assumptions_applied: list[str] = Field(default_factory=list)


class FutureStateForecaster:
    """Projects future state metrics across short, medium, and long-term horizons."""

    HORIZONS = {
        "SHORT_TERM": 300,       # 5 minutes
        "MEDIUM_TERM": 3600,     # 1 hour
        "LONG_TERM": 86400,      # 24 hours
    }

    def forecast_trajectory(
        self,
        baseline_state: dict[str, Any],
        hypothetical_interventions_count: int,
        traffic_growth_rate: float = 0.05,
    ) -> list[HorizonProjection]:
        """Generates trajectory frames across time horizons."""
        projections: list[HorizonProjection] = []

        base_cpu = float(baseline_state.get("cpu_percent", 45.0))
        base_mem = float(baseline_state.get("memory_percent", 50.0))
        base_lat = float(baseline_state.get("p95_latency_ms", 65.0))

        for name, offset_sec in self.HORIZONS.items():
            # Compounding drift/growth
            multiplier = 1.0 + (traffic_growth_rate * (offset_sec / 3600.0))
            projected_cpu = round(min(100.0, base_cpu * multiplier), 2)
            projected_mem = round(min(100.0, base_mem * (1.0 + (multiplier - 1.0) * 0.7)), 2)
            projected_lat = round(base_lat * (1.0 + (multiplier - 1.0) * 0.5), 2)

            # Confidence decays over time
            horizon_conf = 0.90 if name == "SHORT_TERM" else (0.75 if name == "MEDIUM_TERM" else 0.55)

            proj = HorizonProjection(
                horizon_name=name,
                time_offset_seconds=offset_sec,
                projected_metrics={
                    "cpu_percent": projected_cpu,
                    "memory_percent": projected_mem,
                    "p95_latency_ms": projected_lat,
                },
                confidence=horizon_conf,
                assumptions_applied=[
                    f"Traffic growth rate assumed at {traffic_growth_rate * 100}% per hour",
                    "No unpredicted external shock during horizon window",
                ],
            )
            projections.append(proj)

        return projections
