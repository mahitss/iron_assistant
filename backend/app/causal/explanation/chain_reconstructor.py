"""Event Chain Reconstruction for Task 112:
Reconstructs bounded chronological event and state transition sequences leading to a target.

Strict Invariants:
- TEMPORAL ORDER != CAUSATION
- ADJACENT EVENTS ARE NOT AUTOMATICALLY CAUSALLY LINKED
- RECONSTRUCTION PRESERVES TEMPORAL UNCERTAINTY
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.causal.explanation.domain import (
    CausalRelationshipRole,
    EventChain,
    EventChainStep,
    gen_explanation_id,
    utc_now,
)
from app.temporal.domain import (
    StateTransition,
    TemporalClockType,
    TemporalEvent,
    TemporalInterval,
)
from app.temporal.service import TemporalIntelligenceService


class EventChainReconstructor:
    """Extracts and bounds the chronological chain of events and state changes preceding a target."""

    DEFAULT_WINDOW_SECONDS = 3600.0  # 1 hour prior to target
    MAX_CHAIN_STEPS = 50

    @classmethod
    def reconstruct_event_chain(
        cls,
        target_entity: str,
        target_timestamp: Optional[datetime] = None,
        target_event_id: Optional[str] = None,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        max_steps: int = MAX_CHAIN_STEPS,
    ) -> EventChain:
        """Reconstructs the preceding event and transition chain from Temporal Intelligence."""
        t_end = target_timestamp or utc_now()
        t_start = t_end - timedelta(seconds=window_seconds)

        temporal_svc = TemporalIntelligenceService.get_instance()
        timeline = temporal_svc.get_timeline(
            entity_id=target_entity,
            from_time=t_start,
            to_time=t_end,
        )

        raw_events: List[TemporalEvent] = []
        raw_transitions: List[StateTransition] = []

        for seg in timeline.segments:
            raw_events.extend(seg.events)
            raw_transitions.extend(seg.transitions)

        # Sort all raw events by event_time
        raw_events.sort(key=lambda e: e.clocks.event_time)
        raw_transitions.sort(key=lambda t: t.timestamp)

        # Create mapping of event_id -> transition
        trans_by_event: Dict[str, StateTransition] = {}
        for t in raw_transitions:
            if t.trigger_event_id:
                trans_by_event[t.trigger_event_id] = t

        steps: List[EventChainStep] = []
        step_idx = 0

        for e in raw_events:
            step_idx += 1
            trans = trans_by_event.get(e.canonical_event_id)
            state_before = trans.previous_state if trans else None
            state_after = trans.next_state if trans else None

            # Assess whether this event has explicit causation link or is just temporal
            is_causal = bool(e.causation_id or (trans and trans.attributed_cause))

            steps.append(
                EventChainStep(
                    step_index=step_idx,
                    event_id=e.canonical_event_id,
                    event_type=e.event_type,
                    entity_id=e.source_entity_id or target_entity,
                    timestamp=e.clocks.event_time,
                    state_before=state_before,
                    state_after=state_after,
                    source_subsystem=e.source_subsystem,
                    is_causally_linked=is_causal,
                    transition_role=(
                        CausalRelationshipRole.DIRECT_CAUSE if is_causal
                        else CausalRelationshipRole.TEMPORALLY_ASSOCIATED
                    ),
                    evidence_summary=e.payload_summary,
                )
            )
            if len(steps) >= max_steps:
                break

        is_truncated = len(raw_events) > max_steps

        return EventChain(
            target_event_id=target_event_id or f"target_{target_entity}",
            target_entity_id=target_entity,
            start_time=t_start,
            end_time=t_end,
            steps=steps,
            total_steps=len(steps),
            is_truncated=is_truncated,
        )
