"""Cross-Source Event Correlation, Causation vs Observation Separation, and Event Graph (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Set
import uuid

from app.perception.events import PerceptionEvent

logger = logging.getLogger("kairo.perception.correlator")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CorrelationRelation(str, Enum):
    CORRELATED_WITH = "CORRELATED_WITH"
    TRIGGERED = "TRIGGERED"
    OBSERVED_AFTER = "OBSERVED_AFTER"
    HYPOTHESIZED_CAUSE = "HYPOTHESIZED_CAUSE"  # Inferred, never automatically assumed as factual (Spec 26, 27)


@dataclass
class CorrelationEdge:
    """Link connecting two environmental events with explicit causation separation (Spec 24-27)."""

    source_event_id: str
    target_event_id: str
    relation: CorrelationRelation
    confidence: float = 1.0
    is_inferred: bool = False
    evidence: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)


class EventCorrelator:
    """Discovers and links multi-source event sequences (e.g. Git push -> CI -> Deploy -> Health) (Spec 24-28, 133, 134)."""

    def __init__(self) -> None:
        # correlation_id -> list of event_ids
        self._correlation_groups: Dict[str, List[str]] = {}
        # event_id -> list of CorrelationEdges
        self._graph: Dict[str, List[CorrelationEdge]] = {}
        # event_id -> PerceptionEvent
        self._events_by_id: Dict[str, PerceptionEvent] = {}

    def record_event(self, event: PerceptionEvent) -> None:
        """Register event in correlator index and correlation group."""
        self._events_by_id[event.event_id] = event
        cid = event.correlation_id or event.payload.get("commit_hash") or event.payload.get("task_id")
        if cid:
            self._correlation_groups.setdefault(cid, []).append(event.event_id)

    def correlate(
        self,
        source_event_id: str,
        target_event_id: str,
        relation: CorrelationRelation = CorrelationRelation.CORRELATED_WITH,
        confidence: float = 1.0,
        is_inferred: bool = False,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> CorrelationEdge:
        """Explicitly connect two events in the correlation graph (Spec 24-28).
        
        CRITICAL: Causation is represented separately from observed facts! (Spec 26, 27)
        """
        edge = CorrelationEdge(
            source_event_id=source_event_id,
            target_event_id=target_event_id,
            relation=relation,
            confidence=confidence,
            is_inferred=is_inferred,
            evidence=evidence or {},
        )
        self._graph.setdefault(source_event_id, []).append(edge)
        logger.info(
            "Correlated events: %s -[%s]-> %s (inferred=%s, conf=%.2f)",
            source_event_id,
            relation.value,
            target_event_id,
            is_inferred,
            confidence,
        )
        return edge

    def get_correlated_events(self, correlation_id: str) -> List[PerceptionEvent]:
        """Fetch all events sharing a common trace/correlation ID (Spec 25, 134)."""
        event_ids = self._correlation_groups.get(correlation_id, [])
        return [self._events_by_id[eid] for eid in event_ids if eid in self._events_by_id]

    def get_outbound_links(self, event_id: str) -> List[CorrelationEdge]:
        return self._graph.get(event_id, [])
