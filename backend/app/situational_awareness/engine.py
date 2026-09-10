"""Central Situational Awareness & Event Correlation Engine (Task 60)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.situational_awareness.anomaly import AnomalyDetector, anomaly_detector
from app.situational_awareness.attention import AttentionEngine, attention_engine
from app.situational_awareness.audit import SituationalAuditor, situational_auditor
from app.situational_awareness.baselines import BaselineEngine, baseline_engine
from app.situational_awareness.clustering import EventClusterer, event_clusterer
from app.situational_awareness.correlation import EventCorrelator, event_correlator
from app.situational_awareness.deduplication import EventDeduplicator, event_deduplicator
from app.situational_awareness.hypotheses import HypothesisEngine, hypothesis_engine
from app.situational_awareness.impact import ImpactAnalyzer, impact_analyzer
from app.situational_awareness.normalization import EventNormalizer, event_normalizer
from app.situational_awareness.safety import (
    SituationalAwarenessSafetyError,
    sanitize_situation_directive,
)
from app.situational_awareness.schemas import (
    AttentionItem,
    EventIngestRequest,
    NormalizedEvent,
    Situation,
    SituationSeverity,
    SituationStatus,
)
from app.situational_awareness.timelines import TimelineEngine, timeline_engine
from app.situational_awareness.triggers import SituationTriggerBridge, situation_trigger_bridge

logger = logging.getLogger(__name__)


class SituationalAwarenessEngine:
    """Core domain engine coordinating ingestion, correlation, blast radius, hypotheses, and triggers."""

    def __init__(
        self,
        normalizer: EventNormalizer | None = None,
        deduplicator: EventDeduplicator | None = None,
        baselines: BaselineEngine | None = None,
        anomalies: AnomalyDetector | None = None,
        correlator: EventCorrelator | None = None,
        clusterer: EventClusterer | None = None,
        impact_eng: ImpactAnalyzer | None = None,
        hypotheses_eng: HypothesisEngine | None = None,
        attention_eng: AttentionEngine | None = None,
        timelines_eng: TimelineEngine | None = None,
        trigger_bridge: SituationTriggerBridge | None = None,
        auditor: SituationalAuditor | None = None,
    ) -> None:
        self.normalizer = normalizer or event_normalizer
        self.deduplicator = deduplicator or event_deduplicator
        self.baselines = baselines or baseline_engine
        self.anomalies = anomalies or anomaly_detector
        self.correlator = correlator or event_correlator
        self.clusterer = clusterer or event_clusterer
        self.impact_analyzer = impact_eng or impact_analyzer
        self.hypotheses_engine = hypotheses_eng or hypothesis_engine
        self.attention_engine = attention_eng or attention_engine
        self.timeline_engine = timelines_eng or timeline_engine
        self.trigger_bridge = trigger_bridge or situation_trigger_bridge
        self.auditor = auditor or situational_auditor

        # In-memory stores
        self._situations: dict[str, Situation] = {}
        self._events: dict[str, NormalizedEvent] = {}
        self._situation_events_map: dict[str, list[str]] = {}

    def process_event(
        self,
        request: EventIngestRequest,
        dependency_map: dict[str, list[str]] | None = None,
        active_plans: list[dict[str, Any]] | None = None,
        active_goals: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Ingest, normalize, deduplicate, correlate, and update/create operational situations."""
        # 1. Normalize
        event = self.normalizer.normalize(request)

        # 2. Deduplicate
        is_dup, original_id = self.deduplicator.is_duplicate(event)
        if is_dup:
            return {
                "status": "DEDUPLICATED",
                "event_id": event.event_id,
                "original_event_id": original_id,
                "message": "Duplicate event suppressed within sliding window.",
            }

        self._events[event.event_id] = event

        # 3. Check for metric anomalies if numeric observation present in payload
        if "metric_value" in event.payload and event.resource:
            val = float(event.payload["metric_value"])
            anom = self.anomalies.check_observation(
                signal_name=event.event_type,
                resource=event.resource,
                observed_value=val,
                environment=event.environment,
            )
            if anom:
                event.is_anomaly = True

        # 4. Correlation with active situations
        matched_situation: Situation | None = None
        for sit in self._situations.values():
            if sit.status in (SituationStatus.CLOSED, SituationStatus.RESOLVED):
                continue
            # Correlate with events already attached to situation
            sit_event_ids = self._situation_events_map.get(sit.situation_id, [])
            sit_events = [self._events[eid] for eid in sit_event_ids if eid in self._events]

            for member in sit_events:
                corr = self.correlator.correlate_events(event, member, dependency_map)
                if corr["is_correlated"]:
                    matched_situation = sit
                    break
            if matched_situation:
                break

        # 5. Create new situation or update existing
        now = datetime.now(timezone.utc)
        if not matched_situation:
            sit_id = f"sit_{uuid.uuid4().hex[:10]}"
            title = sanitize_situation_directive(f"Operational Event: {event.subject}")
            matched_situation = Situation(
                situation_id=sit_id,
                title=title,
                description=f"Initial observation on {event.resource or 'system'}: {event.subject}",
                status=SituationStatus.DETECTED,
                severity=event.severity,
                confidence=event.confidence,
                environment=event.environment,
                affected_resources=[event.resource] if event.resource else [],
                last_observed_at=event.occurred_at,
            )
            self._situations[sit_id] = matched_situation
            self._situation_events_map[sit_id] = [event.event_id]

            self.auditor.record_event(
                event_type="SITUATION_CREATED",
                actor=event.source,
                situation_id=sit_id,
                details={"title": title, "severity": event.severity.value},
            )
        else:
            self._situation_events_map[matched_situation.situation_id].append(event.event_id)
            if event.resource and event.resource not in matched_situation.affected_resources:
                matched_situation.affected_resources.append(event.resource)
            matched_situation.last_observed_at = max(matched_situation.last_observed_at, event.occurred_at)
            matched_situation.updated_at = now

            # Escalate severity if incoming event has higher severity
            severity_order = {
                SituationSeverity.INFO: 0,
                SituationSeverity.LOW: 1,
                SituationSeverity.MEDIUM: 2,
                SituationSeverity.HIGH: 3,
                SituationSeverity.CRITICAL: 4,
            }
            if severity_order.get(event.severity, 0) > severity_order.get(matched_situation.severity, 0):
                matched_situation.severity = event.severity

        event.situation_id = matched_situation.situation_id

        # 6. Recompute timeline, blast radius, hypotheses, and attention priority
        all_eids = self._situation_events_map.get(matched_situation.situation_id, [])
        all_events = [self._events[eid] for eid in all_eids if eid in self._events]

        matched_situation.timeline = self.timeline_engine.build_timeline(all_events)
        impact = self.impact_analyzer.calculate_blast_radius(
            situation_id=matched_situation.situation_id,
            affected_resources=matched_situation.affected_resources,
            dependency_map=dependency_map,
            active_plans=active_plans,
            active_goals=active_goals,
        )
        matched_situation.affected_services = impact.known_affected_services
        matched_situation.affected_plans = impact.affected_plans
        matched_situation.affected_goals = impact.affected_goals

        matched_situation.hypotheses = self.hypotheses_engine.generate_hypotheses(
            situation_id=matched_situation.situation_id,
            events=all_events,
            affected_resources=matched_situation.affected_resources,
        )

        attention = self.attention_engine.score_attention(matched_situation)

        # 7. Check if triggers should fire
        decision_req = None
        if matched_situation.severity in (SituationSeverity.HIGH, SituationSeverity.CRITICAL):
            decision_req = self.trigger_bridge.generate_decision_request(matched_situation, impact)

        plan_notices = []
        if impact.affected_plans:
            plan_notices = self.trigger_bridge.notify_plan_invalidation(matched_situation, impact)

        return {
            "status": "PROCESSED",
            "event_id": event.event_id,
            "situation_id": matched_situation.situation_id,
            "severity": matched_situation.severity.value,
            "situation_status": matched_situation.status.value,
            "attention_priority": attention.composite_priority,
            "decision_trigger_created": decision_req is not None,
            "plans_impacted_count": len(plan_notices),
        }

    def resolve_situation(
        self,
        situation_id: str,
        actor: str,
        verification_evidence: dict[str, Any],
    ) -> Situation:
        """Resolve situation only when verified.

        Invariant 7 & 44 & 124: Silence != Recovery. Closure requires verification evidence.
        """
        sit = self._situations.get(situation_id)
        if not sit:
            raise SituationalAwarenessSafetyError(f"Situation '{situation_id}' not found.")

        if not verification_evidence or not verification_evidence.get("is_verified", False):
            raise SituationalAwarenessSafetyError(
                f"False Recovery Defense: Situation '{situation_id}' cannot be resolved without verified evidence."
            )

        sit.status = SituationStatus.RESOLVED
        sit.updated_at = datetime.now(timezone.utc)

        # Check flapping
        is_flapping = self.attention_engine.record_transition_and_check_flapping(
            situation_id, SituationStatus.RESOLVED
        )
        if is_flapping:
            sit.flapping_count += 1

        self.auditor.record_event(
            event_type="SITUATION_RESOLVED",
            actor=actor,
            situation_id=situation_id,
            details={"verification_evidence": verification_evidence, "flapping": is_flapping},
        )

        logger.info("SITUATION_RESOLVED: id=%s by=%s", situation_id, actor)
        return sit

    def get_attention_feed(self) -> list[AttentionItem]:
        """Return situations ranked by composite attention priority."""
        active = [
            s
            for s in self._situations.values()
            if s.status not in (SituationStatus.CLOSED, SituationStatus.RESOLVED)
        ]
        items = [self.attention_engine.score_attention(s) for s in active]
        items.sort(key=lambda x: x.composite_priority, reverse=True)
        return items


situational_awareness_engine = SituationalAwarenessEngine()
