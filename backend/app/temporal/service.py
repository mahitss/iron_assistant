"""Temporal Intelligence Service for Task 111:
Authoritative coordinator for multi-clock normalization, deterministic event timelines,
"What Changed?" diffing, causal attribution, and offline catch-up reconstruction.

Strict Invariants:
- EVENT != STATE != CAUSE
- HISTORICAL STATE NEVER MASQUERADES AS CURRENT
- UNATTRIBUTED CHANGES REMAIN UNATTRIBUTED
- EMERGENCY STOP OVERRIDES COGNITION
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple

from app.temporal.attribution_engine import AttributionEngine
from app.temporal.diff_engine import DiffEngine
from app.temporal.domain import (
    AttributionCertainty,
    ChangeCategory,
    ChangeRecord,
    ChangeSet,
    ChangeSummary,
    ExpectedVsActual,
    StateTransition,
    TemporalAnomaly,
    TemporalAnomalyType,
    TemporalCheckpoint,
    TemporalClockType,
    TemporalEntity,
    TemporalEntityType,
    TemporalEvent,
    TemporalGap,
    TemporalInterval,
    TemporalQuery,
    TemporalQueryResult,
    TemporalWatermark,
    Timeline,
    TimelineSegment,
    gen_temporal_id,
    utc_now,
)
from app.temporal.normalization_engine import NormalizationEngine
from app.temporal.ordering_engine import OrderingEngine
from app.temporal.query_engine import QueryEngine
from app.temporal.reconstruction_engine import ReconstructionEngine
from app.temporal.timeline_engine import TimelineEngine

logger = logging.getLogger("kairo.temporal.service")
CACHE_FILE = Path(tempfile.gettempdir()) / "kairo_temporal_cli_cache.json"


class TemporalIntelligenceService:
    """Singleton service orchestrating temporal intelligence across all Kairo subsystems."""

    _instance: "TemporalIntelligenceService | None" = None

    def __init__(self) -> None:
        self._events: Dict[str, TemporalEvent] = {}
        self._seen_canonical_ids: Set[str] = set()
        self._entities: Dict[str, TemporalEntity] = {}
        self._transitions: List[StateTransition] = []
        self._anomalies: List[TemporalAnomaly] = []
        self._gaps: List[TemporalGap] = []
        self._watermarks: Dict[str, TemporalWatermark] = {}
        self._checkpoints: Dict[str, TemporalCheckpoint] = {}
        self._changesets: Dict[str, ChangeSet] = {}
        self._sequence_counter: int = 0
        self._load_from_cache()

    @classmethod
    def get_instance(cls) -> "TemporalIntelligenceService":
        if cls._instance is None:
            cls._instance = TemporalIntelligenceService()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    # ========================================================================
    # Event Ingestion & Normalization
    # ========================================================================

    def ingest_event(
        self,
        event_dict_or_obj: Any,
        ingested_at: Optional[datetime] = None,
        observed_at: Optional[datetime] = None,
    ) -> TemporalEvent:
        """Normalizes and ingests an event, updating order, state, and watermarks."""
        self._sequence_counter += 1
        tevt = NormalizationEngine.normalize(
            event_dict_or_obj=event_dict_or_obj,
            ingested_at=ingested_at,
            observed_at=observed_at,
            sequence_num=self._sequence_counter,
        )

        # 1. Deduplication check
        if tevt.canonical_event_id in self._seen_canonical_ids:
            tevt.is_duplicate = True
            logger.info("Duplicate event observed: %s", tevt.canonical_event_id)
        else:
            self._seen_canonical_ids.add(tevt.canonical_event_id)

        # 2. Out-of-order & Late arrival check
        subsystem = tevt.source_subsystem
        watermark = self._get_or_create_watermark(subsystem)
        ref_watermark = max(watermark.source_watermark, watermark.processing_watermark)
        if tevt.clocks.event_time < watermark.source_watermark:
            tevt.is_out_of_order = True
            lag = (watermark.source_watermark - tevt.clocks.event_time).total_seconds()
            if lag > OrderingEngine.LATE_THRESHOLD_SECONDS:
                tevt.is_late = True
        elif tevt.clocks.event_time < watermark.processing_watermark:
            tevt.is_out_of_order = True
            lag = (watermark.processing_watermark - tevt.clocks.event_time).total_seconds()
            if lag > OrderingEngine.LATE_THRESHOLD_SECONDS:
                tevt.is_late = True

        # 3. Store event
        self._events[tevt.temporal_event_id] = tevt

        # 4. Extract transitions if applicable
        transitions = TimelineEngine.extract_transitions([tevt])
        for t in transitions:
            # Attempt attribution against recent events
            recent_events = list(self._events.values())[-10:]
            t = AttributionEngine.attribute_transition(t, recent_events)
            self._transitions.append(t)
            self._update_entity_state(t)

        # 5. Anomaly detection
        new_anomalies = ReconstructionEngine.detect_anomalies([tevt], transitions=transitions)
        self._anomalies.extend(new_anomalies)

        # 6. Advance watermark
        OrderingEngine.advance_watermark(watermark, [tevt])
        self._save_to_cache()

        return tevt

    # ========================================================================
    # State & Transition Management
    # ========================================================================

    def record_transition(
        self,
        entity_id: str,
        entity_type: TemporalEntityType,
        previous_state: str,
        next_state: str,
        actor: Optional[str] = None,
        attribution: AttributionCertainty = AttributionCertainty.UNATTRIBUTED,
        attributed_cause: Optional[str] = None,
        correlation_id: Optional[str] = None,
        scope: str = "DEFAULT",
        evidence: Optional[List[str]] = None,
    ) -> StateTransition:
        """Explicitly records a state transition."""
        trans = StateTransition(
            entity_id=entity_id,
            entity_type=entity_type,
            previous_state=previous_state,
            next_state=next_state,
            actor=actor,
            timestamp=utc_now(),
            evidence=evidence or [],
            attribution=attribution,
            attributed_cause=attributed_cause,
            correlation_id=correlation_id,
            scope=scope,
        )
        self._transitions.append(trans)
        self._update_entity_state(trans)

        # Check oscillation anomaly
        anomalies = ReconstructionEngine.detect_anomalies([], transitions=self._transitions[-5:])
        self._anomalies.extend(anomalies)

        self._save_to_cache()
        return trans

    def _update_entity_state(self, transition: StateTransition) -> None:
        ent = self._entities.get(transition.entity_id)
        if ent:
            ent.current_version += 1
            ent.current_state = transition.next_state
            ent.last_transition_time = transition.timestamp
        else:
            self._entities[transition.entity_id] = TemporalEntity(
                entity_id=transition.entity_id,
                entity_type=transition.entity_type,
                scope=transition.scope,
                current_state=transition.next_state,
                valid_from=transition.timestamp,
                last_transition_time=transition.timestamp,
            )

    # ========================================================================
    # Query & Timeline Operations
    # ========================================================================

    def get_timeline(
        self,
        entity_id: Optional[str] = None,
        entity_type: Optional[TemporalEntityType] = None,
        scope: str = "DEFAULT",
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> Timeline:
        """Builds a bounded chronological timeline."""
        return TimelineEngine.build_timeline(
            events=list(self._events.values()),
            entity_id=entity_id,
            entity_type=entity_type,
            scope=scope,
            from_time=from_time,
            to_time=to_time,
        )

    def execute_query(self, query: TemporalQuery) -> TemporalQueryResult:
        """Executes a bounded temporal query."""
        return QueryEngine.execute_query(
            query=query,
            events=list(self._events.values()),
            transitions=self._transitions,
            anomalies=self._anomalies,
            gaps=self._gaps,
        )

    def state_as_of(self, entity_id: str, as_of_time: datetime) -> Dict[str, Any]:
        """Evaluates historical state of an entity at time T."""
        ent = self._entities.get(entity_id)
        return QueryEngine.state_as_of(
            entity_id=entity_id,
            as_of_time=as_of_time,
            transitions=self._transitions,
            fallback_entity=ent,
        )

    # ========================================================================
    # "What Changed?" Diff Operations
    # ========================================================================

    def compute_diff(
        self,
        state_a: Dict[str, Any],
        state_b: Dict[str, Any],
        from_reference: str = "checkpoint_a",
        to_reference: str = "checkpoint_b",
        entity_id: str = "global",
        entity_type: TemporalEntityType = TemporalEntityType.SYSTEM,
    ) -> ChangeSet:
        """Computes semantic diff between two state dictionaries."""
        changeset = DiffEngine.compute_diff(
            state_a=state_a,
            state_b=state_b,
            from_reference=from_reference,
            to_reference=to_reference,
            entity_id=entity_id,
            entity_type=entity_type,
        )
        self._changesets[changeset.changeset_id] = changeset
        self._save_to_cache()
        return changeset

    def diff_checkpoints(self, chkp_a_id: str, chkp_b_id: str) -> ChangeSet:
        """Computes diff between two stored checkpoints."""
        chkp_a = self._checkpoints.get(chkp_a_id)
        chkp_b = self._checkpoints.get(chkp_b_id)
        if not chkp_a or not chkp_b:
            raise KeyError(f"One or both checkpoints not found: '{chkp_a_id}', '{chkp_b_id}'")

        return self.compute_diff(
            state_a=chkp_a.active_entity_states,
            state_b=chkp_b.active_entity_states,
            from_reference=chkp_a.name,
            to_reference=chkp_b.name,
            from_time=chkp_a.timestamp,
            to_time=chkp_b.timestamp,
        )

    # ========================================================================
    # Checkpoints & Offline Catch-up Reconstruction
    # ========================================================================

    def create_checkpoint(
        self,
        name: str,
        checkpoint_type: str = "MANUAL",
        entity_states: Optional[Dict[str, str]] = None,
        creator: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TemporalCheckpoint:
        """Captures a stable temporal checkpoint for fast diffing."""
        states = entity_states if entity_states is not None else {
            ent.entity_id: ent.current_state for ent in self._entities.values()
        }
        chkp = TemporalCheckpoint(
            name=name,
            checkpoint_type=checkpoint_type,
            active_entity_states=states,
            creator=creator,
            metadata=metadata or {},
        )
        self._checkpoints[chkp.checkpoint_id] = chkp
        self._save_to_cache()
        return chkp

    def get_checkpoint(self, checkpoint_id: str) -> Optional[TemporalCheckpoint]:
        return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(self) -> List[TemporalCheckpoint]:
        return sorted(self._checkpoints.values(), key=lambda c: c.timestamp, reverse=True)

    def reconcile_offline(
        self,
        subsystem: str,
        prior_state: Dict[str, Any],
        observed_current_state: Dict[str, Any],
        reconnect_time: Optional[datetime] = None,
    ) -> Tuple[ChangeSet, List[TemporalGap]]:
        """Reconciles an offline disconnection period."""
        watermark = self._get_or_create_watermark(subsystem)
        t_reconnect = reconnect_time or utc_now()

        changeset, gaps = ReconstructionEngine.reconcile_offline_period(
            last_watermark=watermark,
            reconnect_time=t_reconnect,
            recovered_events=[],
            prior_state=prior_state,
            observed_current_state=observed_current_state,
        )
        self._gaps.extend(gaps)
        self._changesets[changeset.changeset_id] = changeset
        self._save_to_cache()
        return changeset, gaps

    # ========================================================================
    # Diagnostics & Watermarks
    # ========================================================================

    def list_anomalies(self) -> List[TemporalAnomaly]:
        return sorted(self._anomalies, key=lambda a: a.detected_at, reverse=True)

    def list_gaps(self) -> List[TemporalGap]:
        return sorted(self._gaps, key=lambda g: g.gap_start, reverse=True)

    def list_watermarks(self) -> List[TemporalWatermark]:
        return list(self._watermarks.values())

    def _get_or_create_watermark(self, subsystem: str) -> TemporalWatermark:
        if subsystem not in self._watermarks:
            self._watermarks[subsystem] = TemporalWatermark(subsystem=subsystem)
        return self._watermarks[subsystem]

    # ========================================================================
    # Multi-Process Disk Cache
    # ========================================================================

    def _save_to_cache(self) -> None:
        try:
            cache = {
                "events": {k: json.loads(v.model_dump_json()) for k, v in list(self._events.items())[-200:]},
                "transitions": [json.loads(t.model_dump_json()) for t in self._transitions[-200:]],
                "entities": {k: json.loads(v.model_dump_json()) for k, v in self._entities.items()},
                "anomalies": [json.loads(a.model_dump_json()) for a in self._anomalies[-100:]],
                "gaps": [json.loads(g.model_dump_json()) for g in self._gaps[-100:]],
                "checkpoints": {k: json.loads(v.model_dump_json()) for k, v in self._checkpoints.items()},
                "changesets": {k: json.loads(v.model_dump_json()) for k, v in list(self._changesets.items())[-50:]},
            }
            CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.debug("Failed to write temporal disk cache: %s", exc)

    def _load_from_cache(self) -> None:
        if not CACHE_FILE.exists():
            return
        try:
            raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            for k, d in raw.get("events", {}).items():
                self._events[k] = TemporalEvent.model_validate(d)
                self._seen_canonical_ids.add(self._events[k].canonical_event_id)
            for d in raw.get("transitions", []):
                self._transitions.append(StateTransition.model_validate(d))
            for k, d in raw.get("entities", {}).items():
                self._entities[k] = TemporalEntity.model_validate(d)
            for d in raw.get("anomalies", []):
                self._anomalies.append(TemporalAnomaly.model_validate(d))
            for d in raw.get("gaps", []):
                self._gaps.append(TemporalGap.model_validate(d))
            for k, d in raw.get("checkpoints", {}).items():
                self._checkpoints[k] = TemporalCheckpoint.model_validate(d)
            for k, d in raw.get("changesets", {}).items():
                self._changesets[k] = ChangeSet.model_validate(d)
        except Exception as exc:
            logger.debug("Failed to load temporal disk cache: %s", exc)
