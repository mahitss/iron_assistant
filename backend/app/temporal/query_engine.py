"""Query Engine for Task 111:
Bounded temporal queries and historical "As-Of" state reconstruction.

Strict Invariants:
- HISTORICAL STATE != CURRENT STATE
- NEVER PRESENT HISTORICAL STATE AS CURRENT
- BOUNDED QUERIES ONLY (NO UNBOUNDED SCANS)
- SCOPE ISOLATION ENFORCED
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.temporal.domain import (
    AttributionCertainty,
    StateTransition,
    TemporalAnomaly,
    TemporalEntity,
    TemporalEntityType,
    TemporalEvent,
    TemporalGap,
    TemporalQuery,
    TemporalQueryResult,
    gen_temporal_id,
    utc_now,
)
from app.temporal.ordering_engine import OrderingEngine


class QueryEngine:
    """Executes bounded temporal queries and evaluates point-in-time As-Of states."""

    MAX_QUERY_LIMIT = 1000

    @classmethod
    def execute_query(
        cls,
        query: TemporalQuery,
        events: List[TemporalEvent],
        transitions: List[StateTransition],
        anomalies: List[TemporalAnomaly],
        gaps: List[TemporalGap],
    ) -> TemporalQueryResult:
        """Executes a bounded multi-faceted temporal query."""
        now = utc_now()
        from_t = query.from_time or datetime(1970, 1, 1, tzinfo=UTC)
        to_t = query.to_time or now
        limit = min(query.limit, cls.MAX_QUERY_LIMIT)

        # 1. Filter events
        filtered_events: List[TemporalEvent] = []
        if query.include_events:
            for e in events:
                if not (from_t <= e.clocks.event_time <= to_t):
                    continue
                if query.entity_id and e.source_entity_id != query.entity_id:
                    continue
                if query.category and e.category.upper() != query.category.upper():
                    continue
                if query.scope != "ALL" and e.metadata.get("scope", "DEFAULT") != query.scope:
                    continue
                filtered_events.append(e)

        filtered_events = OrderingEngine.sort_events(filtered_events)[:limit]

        # 2. Filter transitions
        filtered_transitions: List[StateTransition] = []
        if query.include_transitions:
            for t in transitions:
                if not (from_t <= t.timestamp <= to_t):
                    continue
                if query.entity_id and t.entity_id != query.entity_id:
                    continue
                if query.entity_type and t.entity_type != query.entity_type:
                    continue
                if query.attribution and t.attribution != query.attribution:
                    continue
                if query.scope != "ALL" and t.scope != query.scope:
                    continue
                filtered_transitions.append(t)

            filtered_transitions.sort(key=lambda t: t.timestamp)
            filtered_transitions = filtered_transitions[:limit]

        # 3. Filter anomalies
        filtered_anomalies: List[TemporalAnomaly] = []
        if query.include_anomalies:
            for a in anomalies:
                if not (from_t <= a.detected_at <= to_t):
                    continue
                if query.entity_id and a.entity_id != query.entity_id:
                    continue
                filtered_anomalies.append(a)

        # 4. Filter gaps
        filtered_gaps: List[TemporalGap] = []
        if query.include_gaps:
            for g in gaps:
                if not (from_t <= g.gap_start <= to_t):
                    continue
                if query.entity_id and g.entity_id != query.entity_id:
                    continue
                filtered_gaps.append(g)

        total = len(filtered_events) + len(filtered_transitions) + len(filtered_anomalies) + len(filtered_gaps)

        return TemporalQueryResult(
            from_time=from_t,
            to_time=to_t,
            events=filtered_events,
            transitions=filtered_transitions,
            anomalies=filtered_anomalies,
            gaps=filtered_gaps,
            total_count=total,
            is_truncated=total >= limit,
        )

    @classmethod
    def state_as_of(
        cls,
        entity_id: str,
        as_of_time: datetime,
        transitions: List[StateTransition],
        fallback_entity: Optional[TemporalEntity] = None,
    ) -> Dict[str, Any]:
        """Reconstructs the state of an entity at a specific historical point in time.
        
        Strict Invariant:
        The result is explicitly marked with 'is_historical_reconstruction': True.
        """
        # Find all transitions for this entity up to as_of_time
        applicable = [
            t for t in transitions
            if t.entity_id == entity_id and t.timestamp <= as_of_time
        ]

        if not applicable:
            # Fallback or unknown
            if fallback_entity and fallback_entity.valid_from <= as_of_time:
                return {
                    "entity_id": entity_id,
                    "state": fallback_entity.current_state,
                    "as_of_time": as_of_time.isoformat(),
                    "effective_from": fallback_entity.valid_from.isoformat(),
                    "confidence": fallback_entity.confidence,
                    "is_historical_reconstruction": True,
                    "historical_only": True,
                    "source": "entity_baseline",
                }
            return {
                "entity_id": entity_id,
                "state": "UNKNOWN",
                "as_of_time": as_of_time.isoformat(),
                "confidence": 0.0,
                "is_historical_reconstruction": True,
                "historical_only": True,
                "source": "no_prior_transition",
            }

        # Sort chronologically to find the latest transition prior to as_of_time
        applicable.sort(key=lambda t: t.timestamp)
        latest_t = applicable[-1]

        return {
            "entity_id": entity_id,
            "state": latest_t.next_state,
            "as_of_time": as_of_time.isoformat(),
            "effective_from": latest_t.timestamp.isoformat(),
            "last_transition_id": latest_t.transition_id,
            "attribution": latest_t.attribution.value,
            "confidence": latest_t.confidence,
            "is_historical_reconstruction": True,
            "historical_only": True,
            "source": latest_t.actor or "system",
        }

    @classmethod
    def mission_state_as_of(
        cls,
        mission_id: str,
        as_of_time: datetime,
        transitions: List[StateTransition],
    ) -> Dict[str, Any]:
        """Reconstructs mission lifecycle state as of timestamp."""
        return cls.state_as_of(entity_id=mission_id, as_of_time=as_of_time, transitions=transitions)

    @classmethod
    def capability_state_as_of(
        cls,
        capability_id: str,
        as_of_time: datetime,
        transitions: List[StateTransition],
    ) -> Dict[str, Any]:
        """Reconstructs capability readiness state as of timestamp."""
        return cls.state_as_of(entity_id=capability_id, as_of_time=as_of_time, transitions=transitions)
