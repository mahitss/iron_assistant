"""Trend detection, change point identification, and early warning alerting for World Model (Task 65, Spec 28, 29, 33-35, 72, 73)."""

from __future__ import annotations

import logging
from typing import Any

from app.foresight.schemas import (
    EarlyWarningSeverity,
    EarlyWarningSignal,
    TrendDirection,
)

logger = logging.getLogger(__name__)


class EarlyWarningEngine:
    """Detects emerging risks before incidents occur with alert deduplication and storm suppression (Spec 28, 73)."""

    def __init__(self) -> None:
        self._active_warnings: dict[str, EarlyWarningSignal] = {}

    def detect_trend(
        self,
        metric_series: list[float],
        metric_name: str = "metric",
    ) -> dict[str, Any]:
        """Analyze numerical time-series to detect direction and velocity (Spec 33).

        Invariant: TREND != CAUSE (Spec 34). A trend does not automatically imply causation.
        """
        if len(metric_series) < 3:
            return {
                "trend": TrendDirection.STABLE,
                "velocity": 0.0,
                "is_change_point": False,
                "competing_hypotheses": ["Insufficient telemetry samples for causal attribution"],
            }

        diffs = [metric_series[i] - metric_series[i - 1] for i in range(1, len(metric_series))]
        avg_diff = sum(diffs) / len(diffs)

        # Check for change point (sudden spike or regime shift)
        recent_jump = abs(metric_series[-1] - metric_series[-2])
        historical_variance = sum(abs(d) for d in diffs[:-1]) / max(1, len(diffs) - 1)
        is_change_point = recent_jump > (historical_variance * 2.5) and recent_jump > 5.0

        if is_change_point:
            direction = TrendDirection.STRUCTURAL_SHIFT
        elif avg_diff > 1.5:
            # Check for acceleration
            accel = diffs[-1] - diffs[0]
            direction = TrendDirection.ACCELERATING if accel > 0.5 else TrendDirection.INCREASING
        elif avg_diff < -1.5:
            accel = diffs[-1] - diffs[0]
            direction = TrendDirection.DECELERATING if accel < -0.5 else TrendDirection.DECREASING
        else:
            direction = TrendDirection.STABLE

        return {
            "trend": direction,
            "velocity": round(avg_diff, 2),
            "is_change_point": is_change_point,
            "competing_hypotheses": [
                f"Underlying workload growth in {metric_name}",
                f"Upstream resource contention or queuing stall affecting {metric_name}",
                f"Configuration drift or deployment regime change affecting {metric_name}",
            ],
        }

    def emit_early_warning(
        self,
        title: str,
        description: str,
        severity: EarlyWarningSeverity = EarlyWarningSeverity.MEDIUM,
        trend: TrendDirection = TrendDirection.ACCELERATING,
        affected_entities: list[str] | None = None,
        trigger_condition: str = "Threshold trending towards saturation",
        leading_indicators: list[str] | None = None,
        blast_radius: list[str] | None = None,
        recommended_action: str = "Investigate resource allocation and scaling headroom",
    ) -> EarlyWarningSignal:
        """Produce an early warning for an emerging risk (Spec 28).

        Invariant: EARLY WARNING != INCIDENT (Spec 29).
        An early warning indicates 'risk may be increasing', NOT 'incident has occurred'.
        Invariant: ALERT DEDUPLICATION (Spec 73). Avoid alert storms by deduplicating identical cues.
        """
        # Deduplication check: suppress identical active warning storms
        dedup_key = f"{title.lower()}::{','.join(sorted(affected_entities or []))}"
        for existing in self._active_warnings.values():
            if existing.is_active:
                existing_key = f"{existing.title.lower()}::{','.join(sorted(existing.affected_entities))}"
                if existing_key == dedup_key:
                    logger.info("EARLY_WARNING_DEDUPLICATED: title='%s' suppressed as duplicate", title)
                    return existing

        signal = EarlyWarningSignal(
            title=title,
            description=description,
            severity=severity,
            trend=trend,
            affected_entities=affected_entities or [],
            trigger_condition=trigger_condition,
            leading_indicators=leading_indicators or ["Telemetry derivative acceleration"],
            blast_radius=blast_radius or [],
            recommended_action=recommended_action,
            is_active=True,
        )

        self._active_warnings[signal.signal_id] = signal
        logger.warning(
            "EARLY_WARNING_EMITTED: id=%s severity=%s title='%s' trend=%s",
            signal.signal_id,
            severity.value,
            title,
            trend.value,
        )
        return signal

    def resolve_warning(self, signal_id: str) -> bool:
        """Mark an early warning signal as resolved or cleared."""
        if signal_id in self._active_warnings:
            self._active_warnings[signal_id].is_active = False
            return True
        return False

    def list_warnings(
        self,
        severity: EarlyWarningSeverity | None = None,
        active_only: bool = True,
    ) -> list[EarlyWarningSignal]:
        """List early warning signals."""
        results: list[EarlyWarningSignal] = []
        for w in self._active_warnings.values():
            if active_only and not w.is_active:
                continue
            if severity and w.severity != severity:
                continue
            results.append(w)
        return results

    def clear(self) -> None:
        """Clear early warnings cache (for tests)."""
        self._active_warnings.clear()


early_warning_engine = EarlyWarningEngine()
