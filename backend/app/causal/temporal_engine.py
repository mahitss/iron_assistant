"""Temporal causality analysis and causal lag computation (Task 73, Spec 14, 15).

Invariant:
A cause must strictly not occur after its effect in ordinary causal direction.
If effect precedes suspected cause, surface temporal contradiction and reject causation.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.causal.discovery_schemas import TemporalValidationResult

logger = logging.getLogger(__name__)


class TemporalCausalityEngine:
    """Evaluates temporal order, precedence, and causal lag between events."""

    @staticmethod
    def validate_temporal_precedence(
        cause_time: datetime | str,
        effect_time: datetime | str,
        tolerance_seconds: float = 0.0,
    ) -> TemporalValidationResult:
        """Verify that cause preceded effect in time and compute causal lag."""
        c_dt = (
            datetime.fromisoformat(cause_time.replace("Z", "+00:00"))
            if isinstance(cause_time, str)
            else cause_time
        )
        e_dt = (
            datetime.fromisoformat(effect_time.replace("Z", "+00:00"))
            if isinstance(effect_time, str)
            else effect_time
        )

        if c_dt.tzinfo is None:
            c_dt = c_dt.replace(tzinfo=timezone.utc)
        if e_dt.tzinfo is None:
            e_dt = e_dt.replace(tzinfo=timezone.utc)

        delta_seconds = (e_dt - c_dt).total_seconds()

        if delta_seconds < -tolerance_seconds:
            # Contradiction: Effect started before cause!
            reason = (
                f"Temporal Contradiction: Suspected effect occurred at {e_dt.isoformat()}, "
                f"which is {abs(delta_seconds):.1f}s BEFORE suspected cause at {c_dt.isoformat()}. "
                f"Cause cannot explain effect that preceded it."
            )
            return TemporalValidationResult(
                is_temporally_valid=False,
                cause_time=c_dt,
                effect_time=e_dt,
                lag_seconds=delta_seconds,
                contradiction_detected=True,
                contradiction_reason=reason,
            )

        # Valid temporal sequence
        lag = max(0.0, delta_seconds)
        return TemporalValidationResult(
            is_temporally_valid=True,
            cause_time=c_dt,
            effect_time=e_dt,
            lag_seconds=lag,
            contradiction_detected=False,
            contradiction_reason=None,
        )

    @staticmethod
    def analyze_event_sequence(
        events: list[dict[str, Any]],
        cause_event_name: str,
        effect_event_name: str,
    ) -> TemporalValidationResult:
        """Find the earliest cause event and earliest effect event and validate order."""
        earliest_cause: datetime | None = None
        earliest_effect: datetime | None = None

        for ev in events:
            name = ev.get("name") or ev.get("event") or ev.get("type")
            ts = ev.get("timestamp") or ev.get("time")
            if not ts:
                continue
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            if name == cause_event_name:
                if earliest_cause is None or dt < earliest_cause:
                    earliest_cause = dt
            elif name == effect_event_name:
                if earliest_effect is None or dt < earliest_effect:
                    earliest_effect = dt

        if earliest_cause is None or earliest_effect is None:
            return TemporalValidationResult(
                is_temporally_valid=False,
                cause_time=earliest_cause,
                effect_time=earliest_effect,
                contradiction_detected=False,
                contradiction_reason="Insufficient temporal timestamps to establish event ordering.",
            )

        return TemporalCausalityEngine.validate_temporal_precedence(
            cause_time=earliest_cause,
            effect_time=earliest_effect,
        )
