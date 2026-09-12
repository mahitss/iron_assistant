"""Resource Economy Engine: capacity tracking, demand estimation, and saturation management (Task 77)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.orchestration.economy_schemas import (
    DegradationTier,
    EconomyStatusSummary,
    ResourceDemand,
    SaturationState,
)
from app.orchestration.resource_registry import ResourceRegistry, default_resource_registry

logger = logging.getLogger(__name__)


class ResourceEconomyEngine:
    """Master resource economy engine reasoning over finite capacities, demands, and saturation."""

    def __init__(self, resource_registry: ResourceRegistry | None = None) -> None:
        self._registry = resource_registry or default_resource_registry
        self._historical_demands: dict[str, list[float]] = {}  # task_id/capability -> past tokens

    def estimate_demand(
        self,
        task_id: str,
        resource_id: str,
        capability_id: str = "",
        estimated_tokens: int = 1000,
        model_calls: int = 1,
        expected_time_s: float = 1.0,
        priority: int = 1,
        uncertainty_pct: float = 0.15,
        confidence: float = 0.85,
        is_preemptible: bool = True,
    ) -> ResourceDemand:
        """Estimate resource demand with calibrated variance bounds."""
        # Check historical demand to calibrate if available
        key = capability_id or task_id
        past = self._historical_demands.get(key, [])
        if past:
            # Calibrate expected tokens with historical mean
            historical_avg = sum(past) / len(past)
            blended_tokens = int(0.7 * estimated_tokens + 0.3 * historical_avg)
        else:
            blended_tokens = estimated_tokens

        lower = max(0.0, float(blended_tokens) * (1.0 - uncertainty_pct))
        upper = float(blended_tokens) * (1.0 + uncertainty_pct)

        demand = ResourceDemand(
            demand_id=f"dem_{uuid.uuid4().hex[:8]}",
            task_id=task_id,
            resource_id=resource_id,
            capability_id=capability_id,
            estimated_tokens=blended_tokens,
            model_calls=max(1, model_calls),
            expected_time_s=max(0.1, expected_time_s),
            lower_bound=lower,
            upper_bound=upper,
            uncertainty_pct=uncertainty_pct,
            confidence=confidence,
            priority=priority,
            is_preemptible=is_preemptible,
        )

        # Record for future calibration
        if key not in self._historical_demands:
            self._historical_demands[key] = []
        self._historical_demands[key].append(float(blended_tokens))
        if len(self._historical_demands[key]) > 50:
            self._historical_demands[key].pop(0)

        return demand

    def compute_economy_saturation(self) -> tuple[float, SaturationState]:
        """Compute aggregate system saturation percentage across registered resources."""
        resources = self._registry.list_all()
        if not resources:
            return 0.0, SaturationState.HEALTHY

        total_cap = 0.0
        allocated_cap = 0.0
        reserved_cap = 0.0

        for res in resources:
            total_cap += max(1.0, res.total_capacity)
            allocated_cap += res.allocated_capacity
            reserved_cap += res.reserved_capacity

        used_cap = allocated_cap + reserved_cap
        saturation_pct = min(1.0, max(0.0, used_cap / total_cap)) if total_cap > 0 else 0.0

        if saturation_pct >= 0.90:
            state = SaturationState.OVERCOMMITTED
        elif saturation_pct >= 0.75:
            state = SaturationState.SATURATED
        else:
            state = SaturationState.HEALTHY

        return saturation_pct, state

    def recommend_degradation_tier(self, saturation_pct: float | None = None) -> DegradationTier:
        """Recommend system-wide degradation tier based on capacity saturation."""
        if saturation_pct is None:
            saturation_pct, _ = self.compute_economy_saturation()

        if saturation_pct >= 0.95:
            return DegradationTier.EMERGENCY_MINIMAL
        if saturation_pct >= 0.85:
            return DegradationTier.AGGRESSIVE_THROTTLE
        if saturation_pct >= 0.70:
            return DegradationTier.MODERATE_COMPRESSION
        return DegradationTier.FULL_FIDELITY

    def get_summary(self) -> EconomyStatusSummary:
        """Produce top-level summary of resource economy health."""
        resources = self._registry.list_all()
        saturation_pct, state = self.compute_economy_saturation()
        tier = self.recommend_degradation_tier(saturation_pct)

        return EconomyStatusSummary(
            total_resources=len(resources),
            capacity_saturation_pct=saturation_pct,
            saturation_state=state,
            active_degradation_tier=tier,
        )


default_economy_engine = ResourceEconomyEngine()
