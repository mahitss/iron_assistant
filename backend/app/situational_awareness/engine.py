"""Central Situational Awareness, Signal Fusion & Proactive Response Orchestration Engine (Task 60 & Task 99).

Coordinates signal normalization, multi-dimensional correlation, temporal clustering,
situation lifecycle state machines, subsystem bridges, and proactive response loops.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.situational_awareness.anomaly import AnomalyDetector, anomaly_detector
from app.situational_awareness.attention import AttentionEngine, attention_engine
from app.situational_awareness.audit import SituationalAuditor, situational_auditor
from app.situational_awareness.baselines import BaselineEngine, baseline_engine
from app.situational_awareness.bridges import (
    AttentionSubsystemBridge,
    CausalSubsystemBridge,
    ContextSubsystemBridge,
    DecisionSubsystemBridge,
    EmergencyStopBridge,
    ExecutionSubsystemBridge,
    ForecastSubsystemBridge,
    GoalSubsystemBridge,
    KnowledgeGraphSubsystemBridge,
    NotificationSubsystemBridge,
    RiskSubsystemBridge,
    SwarmSubsystemBridge,
    WorldStateSubsystemBridge,
)
from app.situational_awareness.correlation import SignalCorrelator, signal_correlator
from app.situational_awareness.domain import (
    CausalStatus,
    SignalRecord,
    SituationContextRecord,
    SituationInterventionRecord,
    SituationLifecycleState,
    SituationPatternRecord,
    SituationRecord,
    SituationSeverity,
    SituationSuppressionRecord,
    SituationTimelineEntry,
    SituationType,
    SourceTrustLevel,
    StateReconciliationStatus,
)
from app.situational_awareness.hypotheses import HypothesisEngine, hypothesis_engine
from app.situational_awareness.impact import ImpactAnalyzer, impact_analyzer
from app.situational_awareness.lifecycle import SituationLifecycleManager, situation_lifecycle_manager
from app.situational_awareness.normalization import SignalNormalizationPipeline, signal_normalizer
from app.situational_awareness.orchestrator import ProactiveResponseOrchestrator, proactive_orchestrator
from app.situational_awareness.safety import (
    SituationalAwarenessSafetyError,
    SituationStormProtector,
    sanitize_situation_directive,
    storm_protector,
)
from app.situational_awareness.schemas import (
    AttentionItem,
    EventIngestRequest,
    NormalizedEvent,
    Situation,
    SituationStatus,
)
from app.situational_awareness.timelines import TimelineEngine, timeline_engine
from app.situational_awareness.triggers import SituationTriggerBridge, situation_trigger_bridge

logger = logging.getLogger("kairo.situational_awareness.engine")


class SituationalAwarenessEngine:
    """Core domain orchestrator uniting heterogeneous signal fusion with proactive response."""

    def __init__(
        self,
        normalizer: SignalNormalizationPipeline | None = None,
        correlator: SignalCorrelator | None = None,
        lifecycle: SituationLifecycleManager | None = None,
        orchestrator: ProactiveResponseOrchestrator | None = None,
        protector: SituationStormProtector | None = None,
        attention_eng: AttentionEngine | None = None,
        baselines: BaselineEngine | None = None,
        anomalies: AnomalyDetector | None = None,
        impact_eng: ImpactAnalyzer | None = None,
        hypotheses_eng: HypothesisEngine | None = None,
        timelines_eng: TimelineEngine | None = None,
        trigger_bridge: SituationTriggerBridge | None = None,
        auditor: SituationalAuditor | None = None,
    ) -> None:
        self.normalizer = normalizer or signal_normalizer
        self.correlator = correlator or signal_correlator
        self.lifecycle = lifecycle or situation_lifecycle_manager
        self.orchestrator = orchestrator or proactive_orchestrator
        self.protector = protector or storm_protector

        # Auxiliary analytics
        self.attention_engine = attention_eng or attention_engine
        self.baselines = baselines or baseline_engine
        self.anomalies = anomalies or anomaly_detector
        self.impact_analyzer = impact_eng or impact_analyzer
        self.hypotheses_engine = hypotheses_eng or hypothesis_engine
        self.timeline_engine = timelines_eng or timeline_engine
        self.trigger_bridge = trigger_bridge or situation_trigger_bridge
        self.auditor = auditor or situational_auditor

        # Subsystem Bridges
        self.attention_bridge = AttentionSubsystemBridge()
        self.decision_bridge = DecisionSubsystemBridge()
        self.execution_bridge = ExecutionSubsystemBridge()
        self.world_state_bridge = WorldStateSubsystemBridge()
        self.graph_bridge = KnowledgeGraphSubsystemBridge()
        self.context_bridge = ContextSubsystemBridge()
        self.swarm_bridge = SwarmSubsystemBridge()
        self.emergency_bridge = EmergencyStopBridge()
        self.risk_bridge = RiskSubsystemBridge()
        self.forecast_bridge = ForecastSubsystemBridge()
        self.causal_bridge = CausalSubsystemBridge()
        self.goal_bridge = GoalSubsystemBridge()
        self.notification_bridge = NotificationSubsystemBridge()

        # In-memory stores
        self._situations: dict[str, SituationRecord] = {}
        self._signals: dict[str, SignalRecord] = {}
        self._events: dict[str, NormalizedEvent] = {}  # Backward compatibility
        self._situation_signals_map: dict[str, list[str]] = {}
        self._situation_events_map: dict[str, list[str]] = {}  # Backward compatibility
        self._suppressions: dict[str, SituationSuppressionRecord] = {}
        self._interventions: dict[str, SituationInterventionRecord] = {}
        self._contexts: dict[str, SituationContextRecord] = {}

    def process_signal(
        self,
        signal: SignalRecord,
        active_plans: list[dict[str, Any]] | None = None,
        active_goals: list[dict[str, Any]] | None = None,
        dependency_map: dict[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """Core Task 99 ingestion pipeline: Storm protection -> Correlation -> Lifecycle -> Intelligence -> Orchestration."""
        # 1. Storm Protection & Admission Control
        active_count = sum(
            1 for s in self._situations.values()
            if s.lifecycle_state not in (SituationLifecycleState.RESOLVED, SituationLifecycleState.EXPIRED, SituationLifecycleState.SUPPRESSED)
        )
        admission = self.protector.check_signal_admission(signal.source_type, active_count)
        if not admission.admitted:
            return {
                "status": "THROTTLED",
                "signal_id": signal.signal_id,
                "reason": admission.reason,
                "backpressure": admission.backpressure_active,
            }

        # 2. Deduplication check
        is_dup, orig_sig_id = self.correlator.check_and_deduplicate(signal)
        if is_dup:
            if orig_sig_id and orig_sig_id in self._signals:
                orig_signal = self._signals[orig_sig_id]
                # If original signal is attached to a situation, record persistence
                for sit_id, sids in self._situation_signals_map.items():
                    if orig_sig_id in sids and sit_id in self._situations:
                        sit = self._situations[sit_id]
                        sit.signal_count += 1
                        sit.last_signal_at = signal.observed_at
                        sit.last_observed_at = signal.observed_at
                        if sit.signal_count >= 5 and sit.lifecycle_state == SituationLifecycleState.ACTIVE:
                            self.lifecycle.transition_situation(
                                sit, SituationLifecycleState.ESCALATING,
                                actor=signal.source_type, reason="Signal recurrence frequency escalating"
                            )
            return {
                "status": "DEDUPLICATED",
                "signal_id": signal.signal_id,
                "original_signal_id": orig_sig_id,
                "message": "Duplicate signal deduplicated within sliding time window.",
            }

        self._signals[signal.signal_id] = signal

        # 3. Multi-dimensional correlation with active situations
        matched_situation: SituationRecord | None = None
        best_score = 0.0

        for sit in self._situations.values():
            if sit.lifecycle_state in (
                SituationLifecycleState.RESOLVED,
                SituationLifecycleState.EXPIRED,
                SituationLifecycleState.SUPPRESSED,
            ):
                continue

            sit_sig_ids = self._situation_signals_map.get(sit.id, [])
            sit_signals = [self._signals[sid] for sid in sit_sig_ids if sid in self._signals]

            for member in sit_signals:
                score, dimensions = self.correlator.correlate_signals(signal, member)
                if score > best_score and score >= 0.40:
                    best_score = score
                    matched_situation = sit
                    break

        now = datetime.now(timezone.utc)

        # 4. Form new situation or correlate into existing
        if not matched_situation:
            sit_type = SituationType.INCIDENT
            sig_type_upper = signal.signal_type.upper()
            if "DRIFT" in sig_type_upper or "CONFLICT" in sig_type_upper:
                sit_type = SituationType.ANOMALY
            elif "RISK" in sig_type_upper:
                sit_type = SituationType.RISK
            elif "DEGRADATION" in sig_type_upper or "RELIABILITY" in sig_type_upper:
                sit_type = SituationType.DEGRADATION
            elif "CAPABILITY" in sig_type_upper:
                sit_type = SituationType.CAPABILITY_EVENT
            elif "RESOURCE" in sig_type_upper:
                sit_type = SituationType.RESOURCE_PRESSURE
            elif "OPPORTUNITY" in sig_type_upper or "OPTIMIZATION" in sig_type_upper:
                sit_type = SituationType.OPPORTUNITY

            # Map trust and severity
            sig_sev_str = signal.metadata.get("severity") or signal.payload.get("severity")
            sev = SituationSeverity.MEDIUM
            if sig_sev_str:
                try:
                    sev = SituationSeverity(sig_sev_str)
                except Exception:
                    pass

            title = sanitize_situation_directive(f"{sit_type.value}: {signal.subject}")
            matched_situation = self.lifecycle.create_situation(
                situation_type=sit_type,
                title=title,
                summary=f"Initial signal from {signal.source_type} on {signal.entity or 'system'}: {signal.subject}",
                severity=sev,
                confidence=signal.confidence,
                initial_signals=[signal],
                tenant_id=signal.scope,
                project_id=signal.payload.get("project_id"),
            )
            self._situations[matched_situation.id] = matched_situation
            self._situation_signals_map[matched_situation.id] = [signal.signal_id]

            self.auditor.record_event(
                event_type="SITUATION_DETECTED",
                actor=signal.source_type,
                situation_id=matched_situation.id,
                details={"title": title, "severity": sev.value, "type": sit_type.value},
            )
        else:
            self._situation_signals_map[matched_situation.id].append(signal.signal_id)
            matched_situation.signal_count += 1
            matched_situation.last_signal_at = signal.observed_at
            matched_situation.last_observed_at = max(matched_situation.last_observed_at, signal.observed_at)
            matched_situation.updated_at = now
            if signal.entity and signal.entity not in matched_situation.affected_entities:
                matched_situation.affected_entities.append(signal.entity)
            if signal.payload.get("resource") and signal.payload["resource"] not in matched_situation.affected_resources:
                matched_situation.affected_resources.append(signal.payload["resource"])

            # Check for severity escalation
            sev_rank = {
                SituationSeverity.INFO: 0,
                SituationSeverity.LOW: 1,
                SituationSeverity.MEDIUM: 2,
                SituationSeverity.HIGH: 3,
                SituationSeverity.CRITICAL: 4,
            }
            sig_sev_str = signal.metadata.get("severity") or signal.payload.get("severity")
            if sig_sev_str:
                try:
                    new_sev = SituationSeverity(sig_sev_str)
                    if sev_rank.get(new_sev, 0) > sev_rank.get(matched_situation.severity, 0):
                        matched_situation.severity = new_sev
                        matched_situation.timeline.append(
                            SituationTimelineEntry(
                                event_type="SEVERITY_ESCALATED",
                                summary=f"Severity escalated to {new_sev.value} due to signal {signal.signal_id}",
                                timestamp=now,
                            )
                        )
                except Exception:
                    pass

            # Evaluate lifecycle progression
            if matched_situation.lifecycle_state == SituationLifecycleState.DETECTED and matched_situation.signal_count >= 2:
                self.lifecycle.transition_situation(
                    matched_situation, SituationLifecycleState.FORMING,
                    actor=signal.source_type, reason="Multiple correlated signals accumulated"
                )
            elif matched_situation.lifecycle_state == SituationLifecycleState.FORMING and matched_situation.signal_count >= 3:
                self.lifecycle.transition_situation(
                    matched_situation, SituationLifecycleState.ACTIVE,
                    actor=signal.source_type, reason="Situation confirmed active via multi-signal convergence"
                )

        signal.metadata["situation_id"] = matched_situation.id

        # 5. Timeline update
        timeline_entry = SituationTimelineEntry(
            timestamp=signal.observed_at,
            event_type=signal.signal_type,
            summary=signal.subject,
            evidence_id=signal.signal_id,
            is_inference=False,
            metadata={
                "source": signal.source_type,
                "severity": matched_situation.severity.value,
                "evidence_type": "OBSERVED" if signal.trust_classification != SourceTrustLevel.UNTRUSTED_EXTERNAL else "UNTRUSTED",
                "details": signal.payload,
            },
        )
        matched_situation.timeline.append(timeline_entry)

        # 6. Check for Pattern Recognition
        pattern = self.lifecycle.record_and_check_pattern(matched_situation)
        if pattern and pattern.recurrence_count >= 3:
            logger.info("Recurring situation pattern detected: %s (seen %d times)", pattern.pattern_name, pattern.recurrence_count)

        # 7. Subsystem integrations (Attention, Context, Graph)
        context = self.context_bridge.build_situation_context(matched_situation)
        self._contexts[matched_situation.id] = context
        attention_score = self.attention_bridge.submit_situation_candidate(matched_situation)
        self.graph_bridge.record_situation_nodes_and_edges(matched_situation)

        # 8. Trigger Proactive Response Orchestration if situation is ACTIVE or ESCALATING
        orchestration_result = None
        if matched_situation.lifecycle_state in (SituationLifecycleState.ACTIVE, SituationLifecycleState.ESCALATING):
            orchestration_result = self.orchestrator.deliberate_and_respond(matched_situation)

        return {
            "status": "PROCESSED",
            "signal_id": signal.signal_id,
            "situation_id": matched_situation.id,
            "lifecycle_state": matched_situation.lifecycle_state.value,
            "severity": matched_situation.severity.value,
            "attention_priority": attention_score,
            "signal_count": matched_situation.signal_count,
            "proactive_action_status": orchestration_result.get("action_status") if orchestration_result else "NONE",
            "decision_id": matched_situation.current_decision_id,
            "action_transaction_id": matched_situation.current_action_transaction_id,
        }

    def process_event(
        self,
        request: EventIngestRequest,
        dependency_map: dict[str, list[str]] | None = None,
        active_plans: list[dict[str, Any]] | None = None,
        active_goals: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Legacy Task 60 backward-compatible ingestion adapter delegating to Task 99 pipeline."""
        signal = self.normalizer.normalize_legacy_event(request)
        self._events[signal.signal_id] = NormalizedEvent(
            event_id=signal.signal_id,
            event_type=signal.signal_type,
            source=signal.source_type,
            source_trust=signal.trust_classification.value,
            environment=signal.scope,
            resource=signal.entity,
            subject=signal.subject,
            payload=signal.payload,
            severity=signal.payload.get("severity", "INFO"),
            confidence=signal.confidence,
            occurred_at=signal.observed_at,
            received_at=signal.received_at,
        )

        res = self.process_signal(signal, active_plans=active_plans, active_goals=active_goals, dependency_map=dependency_map)
        # Adapt keys for Task 60 caller expectations
        return {
            "status": res.get("status", "PROCESSED"),
            "event_id": signal.signal_id,
            "situation_id": res.get("situation_id", ""),
            "severity": res.get("severity", "MEDIUM"),
            "situation_status": res.get("lifecycle_state", "DETECTED"),
            "attention_priority": res.get("attention_priority", 0.5),
            "decision_trigger_created": res.get("proactive_action_status") in ("ACTION_INITIATED", "ACTION_APPROVED"),
            "plans_impacted_count": 0,
        }

    def resolve_situation(
        self,
        situation_id: str,
        actor: str,
        verification_evidence: dict[str, Any],
    ) -> SituationRecord:
        """Resolve situation only when verified. Silence != Recovery. Closure requires verification evidence."""
        sit = self._situations.get(situation_id)
        if not sit:
            raise SituationalAwarenessSafetyError(f"Situation '{situation_id}' not found.")

        if not verification_evidence or not verification_evidence.get("is_verified", False):
            raise SituationalAwarenessSafetyError(
                f"False Recovery Defense: Situation '{situation_id}' cannot be resolved without verified evidence."
            )

        self.lifecycle.transition_situation(
            sit, SituationLifecycleState.RESOLVED, actor=actor, reason="Verified state convergence confirmed"
        )
        sit.state_reconciliation_status = StateReconciliationStatus.VERIFIED_MATCH
        sit.resolved_at = datetime.now(timezone.utc)

        self.auditor.record_event(
            event_type="SITUATION_RESOLVED",
            actor=actor,
            situation_id=situation_id,
            details={"verification_evidence": verification_evidence},
        )
        return sit

    def suppress_situation(
        self,
        situation_id: str,
        suppressed_by: str,
        reason: str,
        duration_seconds: int = 3600,
    ) -> SituationSuppressionRecord:
        """Auditably suppress situation according to user or maintenance policy."""
        sit = self._situations.get(situation_id)
        if not sit:
            raise SituationalAwarenessSafetyError(f"Situation '{situation_id}' not found.")

        record = self.lifecycle.suppress_situation(sit, suppressed_by, reason, duration_seconds)
        self._suppressions[record.suppression_id] = record
        self.auditor.record_event(
            event_type="SITUATION_SUPPRESSED",
            actor=suppressed_by,
            situation_id=situation_id,
            details={"reason": reason, "duration_seconds": duration_seconds},
        )
        return record

    def reopen_situation(self, situation_id: str, actor: str, reason: str) -> SituationRecord:
        """Reopen a previously resolved or suppressed situation."""
        sit = self._situations.get(situation_id)
        if not sit:
            raise SituationalAwarenessSafetyError(f"Situation '{situation_id}' not found.")

        self.lifecycle.transition_situation(
            sit, SituationLifecycleState.ACTIVE, actor=actor, reason=reason
        )
        self.auditor.record_event(
            event_type="SITUATION_REOPENED",
            actor=actor,
            situation_id=situation_id,
            details={"reason": reason},
        )
        return sit

    def investigate_situation(self, situation_id: str, scope: str | None = None) -> dict[str, Any]:
        """Trigger multi-agent investigation tasks across bounded agents for evidence gathering."""
        sit = self._situations.get(situation_id)
        if not sit:
            raise SituationalAwarenessSafetyError(f"Situation '{situation_id}' not found.")

        # Check emergency stop before delegating investigation
        if self.emergency_bridge.is_stopped():
            return {
                "situation_id": situation_id,
                "investigation_status": "BLOCKED_EMERGENCY_STOP",
                "evidence_collected": [],
            }

        evidence = self.swarm_bridge.delegate_investigation(sit, investigation_scope=scope)
        for ev in evidence:
            sit.evidence.append(ev)

        return {
            "situation_id": situation_id,
            "status": "INVESTIGATION_DISPATCHED",
            "investigation_status": "COMPLETED",
            "evidence_count": len(evidence),
            "evidence": evidence,
        }

    def get_attention_feed(self) -> list[AttentionItem]:
        """Return situations ranked by attention priority."""
        active = [
            s for s in self._situations.values()
            if s.lifecycle_state not in (SituationLifecycleState.RESOLVED, SituationLifecycleState.EXPIRED, SituationLifecycleState.SUPPRESSED)
        ]
        items = []
        for s in active:
            score = self.attention_bridge.submit_situation_candidate(s)
            items.append(
                AttentionItem(
                    situation_id=s.id,
                    title=s.title,
                    severity=s.severity,
                    composite_priority=score,
                    reason=f"Priority {score:.2f} based on urgency {s.urgency:.2f} and blast radius",
                    recommended_action=s.recommended_next_step or "Monitor situation",
                )
            )
        items.sort(key=lambda x: x.composite_priority, reverse=True)
        return items

    def get_stats(self) -> dict[str, Any]:
        """Aggregate real-time statistics across situations, signals, and interventions."""
        total = len(self._situations)
        active = sum(1 for s in self._situations.values() if s.lifecycle_state == SituationLifecycleState.ACTIVE)
        escalating = sum(1 for s in self._situations.values() if s.lifecycle_state == SituationLifecycleState.ESCALATING)
        suppressed = sum(1 for s in self._situations.values() if s.lifecycle_state == SituationLifecycleState.SUPPRESSED)
        resolved = sum(1 for s in self._situations.values() if s.lifecycle_state == SituationLifecycleState.RESOLVED)
        interventions_active = sum(1 for s in self._situations.values() if s.lifecycle_state == SituationLifecycleState.INTERVENTION_ACTIVE)
        unknown = sum(1 for s in self._situations.values() if s.lifecycle_state == SituationLifecycleState.UNKNOWN)

        return {
            "total_situations": total,
            "active_situations": active,
            "escalating_situations": escalating,
            "suppressed_situations": suppressed,
            "resolved_situations": resolved,
            "interventions_active": interventions_active,
            "unknown_situations": unknown,
            "signals_ingested": len(self._signals),
            "patterns_detected": len(self.lifecycle._patterns),
            "emergency_stop_active": self.emergency_bridge.is_stopped(),
        }


# Global singleton instance
situational_awareness_engine = SituationalAwarenessEngine()
