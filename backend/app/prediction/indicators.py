"""Leading Indicator Subsystem (Task 74, Spec 20).

Tracks:
- Early-signaling telemetry preceding target outcome shifts
- Empirical reliability scoring
- Lead-time expectations
- Active deviations from baseline
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.prediction.schemas import LeadingIndicatorSignal

logger = logging.getLogger("kairo.prediction.indicators")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class LeadingIndicatorRegistry:
    """Manages empirical leading indicator relationships and their reliability (Spec 20)."""

    def __init__(self) -> None:
        self._indicators: Dict[str, LeadingIndicatorSignal] = {}
        # indicator_id -> list of bool (whether deviation led to target event within window)
        self._historical_hits: Dict[str, List[bool]] = {}

    def register_indicator(
        self,
        indicator_id: str,
        name: Optional[str] = None,
        target_metric: Optional[str] = None,
        direction: str = "increasing",
        lead_time_seconds: Optional[int] = None,
        baseline_value: float = 0.0,
        historical_reliability: float = 0.8,
        evidence_refs: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> LeadingIndicatorSignal:
        """Register a tracked leading indicator backed by evidence or designated hypothesis."""
        effective_name = name or kwargs.get("relationship") or indicator_id
        effective_target = target_metric or kwargs.get("target") or "unknown_metric"

        if lead_time_seconds is None:
            if "expected_lead_time_minutes" in kwargs:
                lead_time_seconds = int(kwargs["expected_lead_time_minutes"] * 60)
            else:
                lead_time_seconds = 3600

        current_val = float(kwargs.get("current_value", baseline_value))
        deviation = current_val - baseline_value

        signal = LeadingIndicatorSignal(
            indicator_id=indicator_id,
            name=effective_name,
            target_metric=effective_target,
            direction=direction,
            lead_time_seconds=lead_time_seconds,
            historical_reliability=max(0.1, min(1.0, historical_reliability)),
            current_value=current_val,
            baseline_value=baseline_value,
            deviation=deviation,
            is_active=abs(deviation) > 0,
            evidence_refs=evidence_refs or [kwargs.get("relationship", "historical_correlation_analysis")],
            freshness_timestamp=_now_utc().isoformat(),
        )
        self._indicators[indicator_id] = signal
        logger.info("Registered leading indicator '%s' targeting '%s'", effective_name, effective_target)
        return signal

    def update_telemetry(
        self,
        indicator_id: str,
        new_value: float,
        threshold_deviation: float = 2.0,
    ) -> Optional[LeadingIndicatorSignal]:
        """Ingest fresh observation for indicator, calculate deviation, and toggle active status."""
        ind = self._indicators.get(indicator_id)
        if not ind:
            return None

        ind.current_value = new_value
        ind.deviation = new_value - ind.baseline_value
        ind.freshness_timestamp = _now_utc().isoformat()

        # Check activation based on direction
        if ind.direction == "increasing":
            ind.is_active = ind.deviation >= threshold_deviation
        elif ind.direction == "decreasing":
            ind.is_active = ind.deviation <= -threshold_deviation
        else:
            ind.is_active = abs(ind.deviation) >= threshold_deviation

        return ind

    def record_lead_verification(self, indicator_id: str, preceded_event: bool) -> float:
        """Records whether indicator correctly anticipated realized outcome to update reliability."""
        hits = self._historical_hits.setdefault(indicator_id, [])
        hits.append(preceded_event)

        ind = self._indicators.get(indicator_id)
        if ind:
            n = len(hits)
            positives = sum(1 for h in hits if h)
            reliability = positives / max(1, n)
            ind.historical_reliability = round(reliability, 4)
            return ind.historical_reliability
        return 0.5

    def record_observation(self, indicator_id: str, target_occurred: bool) -> float:
        """Alias for record_lead_verification."""
        return self.record_lead_verification(indicator_id, preceded_event=target_occurred)

    def get_indicators_for_target(self, target_metric: str, active_only: bool = False) -> List[LeadingIndicatorSignal]:
        res = [ind for ind in self._indicators.values() if ind.target_metric == target_metric]
        if active_only:
            res = [ind for ind in res if ind.is_active]
        return res

    def get_indicator(self, indicator_id: str) -> Optional[LeadingIndicatorSignal]:
        return self._indicators.get(indicator_id)

    def list_all(self) -> List[LeadingIndicatorSignal]:
        return list(self._indicators.values())


leading_indicator_registry = LeadingIndicatorRegistry()
