"""Timeline Engine for Task 111:
Constructs chronological timelines and extracts explicit state transitions.

Strict Invariants:
- EVENT != STATE
- STATE != EVENT
- OBSERVATION != TRUTH
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Dict, List, Optional

from app.temporal.domain import (
    AttributionCertainty,
    ExpectationStatus,
    StateTransition,
    TemporalEntity,
    TemporalEntityType,
    TemporalEvent,
    Timeline,
    TimelineSegment,
    gen_temporal_id,
    utc_now,
)
from app.temporal.ordering_engine import OrderingEngine


class TimelineEngine:
    """Assembles unified and entity-specific timelines from temporal event streams."""

    STATE_EXTRACTORS: Dict[str, Dict[str, str]] = {
        # Event type -> (previous_state_field, next_state_field)
        "action.started": {"prev": "READY", "next": "EXECUTING"},
        "action.succeeded": {"prev": "EXECUTING", "next": "SUCCEEDED"},
        "action.failed": {"prev": "EXECUTING", "next": "FAILED"},
        "mission.created": {"prev": "NONE", "next": "DRAFT"},
        "mission.activated": {"prev": "DRAFT", "next": "ACTIVE"},
        "mission.at_risk": {"prev": "ACTIVE", "next": "AT_RISK"},
        "mission.paused": {"prev": "ACTIVE", "next": "PAUSED"},
        "mission.completed": {"prev": "ACTIVE", "next": "COMPLETED"},
        "capability.degraded": {"prev": "READY", "next": "DEGRADED"},
        "capability.recovered": {"prev": "DEGRADED", "next": "READY"},
        "belief.formed": {"prev": "PROVISIONAL", "next": "CONFIRMED"},
        "belief.revised": {"prev": "CONFIRMED", "next": "REVISED"},
        "decision.evaluated": {"prev": "DELIBERATING", "next": "DECIDED"},
        "world.reconciled": {"prev": "DRIFTED", "next": "SYNCHRONIZED"},
    }

    @classmethod
    def build_timeline(
        cls,
        events: List[TemporalEvent],
        entity_id: Optional[str] = None,
        entity_type: Optional[TemporalEntityType] = None,
        scope: str = "DEFAULT",
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> Timeline:
        """Constructs a deterministic timeline bounded by time and optional entity filter."""
        filtered = events
        if entity_id:
            filtered = [e for e in filtered if e.source_entity_id == entity_id]
        if from_time:
            filtered = [e for e in filtered if e.clocks.event_time >= from_time]
        if to_time:
            filtered = [e for e in filtered if e.clocks.event_time <= to_time]

        sorted_events = OrderingEngine.sort_events(filtered)

        # Extract state transitions
        transitions = cls.extract_transitions(sorted_events, entity_type=entity_type)

        now = utc_now()
        start = from_time or (sorted_events[0].clocks.event_time if sorted_events else now)
        end = to_time or (sorted_events[-1].clocks.event_time if sorted_events else now)

        segment = TimelineSegment(
            start_time=start,
            end_time=end,
            events=sorted_events,
            transitions=transitions,
        )

        return Timeline(
            entity_id=entity_id,
            entity_type=entity_type,
            scope=scope,
            start_time=start,
            end_time=end,
            total_events=len(sorted_events),
            total_transitions=len(transitions),
            segments=[segment],
        )

    @classmethod
    def extract_transitions(
        cls,
        events: List[TemporalEvent],
        entity_type: Optional[TemporalEntityType] = None,
    ) -> List[StateTransition]:
        """Extracts explicit state transitions from state-modifying events."""
        transitions: List[StateTransition] = []
        entity_state_tracker: Dict[str, str] = {}

        for e in events:
            # Check payload diff for explicit state change
            prev_s = e.payload_diff.get("previous_state") or e.payload_diff.get("from_state")
            next_s = e.payload_diff.get("next_state") or e.payload_diff.get("to_state") or e.payload_diff.get("new_state")

            if not (prev_s and next_s):
                mapping = cls.STATE_EXTRACTORS.get(e.event_type.lower())
                if mapping:
                    prev_s = mapping["prev"]
                    next_s = mapping["next"]

            if prev_s and next_s:
                ent_id = e.source_entity_id or e.canonical_event_id
                # Deduce entity type from event category
                mapped_type = entity_type or cls._map_category_to_entity_type(e.category)

                # Prior state tracking
                actual_prev = entity_state_tracker.get(ent_id, prev_s)

                trans = StateTransition(
                    entity_id=ent_id,
                    entity_type=mapped_type,
                    previous_state=str(actual_prev),
                    next_state=str(next_s),
                    trigger_event_id=e.canonical_event_id,
                    actor=e.actor_id or e.source_subsystem,
                    timestamp=e.clocks.event_time,
                    expectation_status=ExpectationStatus.OBSERVED,
                    evidence=[e.payload_summary],
                    confidence=e.confidence,
                    attribution=AttributionCertainty.DIRECTLY_ATTRIBUTED if e.actor_id else AttributionCertainty.UNATTRIBUTED,
                    attributed_cause=e.causation_id,
                    correlation_id=e.correlation_id,
                )
                transitions.append(trans)
                entity_state_tracker[ent_id] = str(next_s)

        return transitions

    @staticmethod
    def _map_category_to_entity_type(category: str) -> TemporalEntityType:
        cat_upper = category.upper()
        for et in TemporalEntityType:
            if et.value == cat_upper:
                return et
        return TemporalEntityType.SYSTEM
