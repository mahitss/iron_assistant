"""Event correlation across temporal, topological, and dependency dimensions (Task 60)."""

from __future__ import annotations

import logging
from typing import Any

from app.situational_awareness.schemas import NormalizedEvent

logger = logging.getLogger(__name__)


class EventCorrelator:
    """Evaluates multi-dimensional correlation between incoming events.

    Invariant 15: Correlation != Causation.
    Correlated events establish circumstantial evidence, not definitive causal links.
    """

    def __init__(self, temporal_window_seconds: float = 300.0) -> None:
        self._temporal_window = temporal_window_seconds

    def correlate_events(
        self,
        event_a: NormalizedEvent,
        event_b: NormalizedEvent,
        dependency_map: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """Assess temporal, resource, and topological correlation between two events."""
        # Environment check: different environments rarely correlate to the same local incident
        if event_a.environment.lower() != event_b.environment.lower():
            return {
                "is_correlated": False,
                "correlation_score": 0.0,
                "reasons": ["Mismatched environments"],
            }

        # 1. Temporal correlation
        time_diff = abs((event_a.occurred_at - event_b.occurred_at).total_seconds())
        is_temporally_close = time_diff <= self._temporal_window
        temporal_score = max(0.0, 1.0 - (time_diff / self._temporal_window)) if is_temporally_close else 0.0

        # 2. Resource / Subject match
        same_resource = bool(
            event_a.resource and event_b.resource and event_a.resource.lower() == event_b.resource.lower()
        )
        same_subject = event_a.subject.lower() == event_b.subject.lower()
        resource_score = 1.0 if same_resource else (0.5 if same_subject else 0.0)

        # 3. Dependency relationship
        deps = dependency_map or {}
        is_dependent = False
        if event_a.resource and event_b.resource:
            res_a = event_a.resource.lower()
            res_b = event_b.resource.lower()
            if res_a in deps.get(res_b, []) or res_b in deps.get(res_a, []):
                is_dependent = True

        dependency_score = 1.0 if is_dependent else 0.0

        # Composite correlation score
        composite = (temporal_score * 0.4) + (resource_score * 0.4) + (dependency_score * 0.2)
        is_correlated = (
            (same_resource and is_temporally_close)
            or (is_dependent and is_temporally_close)
            or composite >= 0.5
        )

        reasons = []
        if is_temporally_close:
            reasons.append(f"Occurred within {time_diff:.1f}s window")
        if same_resource:
            reasons.append(f"Share identical resource '{event_a.resource}'")
        if is_dependent:
            reasons.append("Linked via service dependency graph")

        return {
            "is_correlated": is_correlated,
            "correlation_score": round(composite, 3),
            "time_difference_seconds": round(time_diff, 1),
            "reasons": reasons,
            "temporal_relationship": "BEFORE" if event_a.occurred_at < event_b.occurred_at else "AFTER",
        }


event_correlator = EventCorrelator()
