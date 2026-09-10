"""Central domain engine coordinating incident triage, investigation, recovery, and learning (Task 61)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.incident_response.audit import IncidentAuditor, incident_auditor
from app.incident_response.checkpoints import CheckpointManager, checkpoint_manager
from app.incident_response.hypotheses import HypothesisManager, hypothesis_manager
from app.incident_response.investigation import InvestigationEngine, investigation_engine
from app.incident_response.learning import IncidentLearningEngine, incident_learning_engine
from app.incident_response.mitigation import MitigationEngine, mitigation_engine
from app.incident_response.options import ResponseOptionEngine, response_option_engine
from app.incident_response.postmortem import PostmortemEngine, postmortem_engine
from app.incident_response.reconciliation import IncidentReconciler, incident_reconciler
from app.incident_response.recovery import recovery_engine
from app.incident_response.safety import (
    IncidentResponseSafetyError,
    sanitize_incident_directive,
    verify_separation_of_duties,
)
from app.incident_response.schemas import (
    ActionState,
    EvidenceItem,
    IncidentResponse,
    IncidentSeverity,
    IncidentStatus,
    IncidentUrgency,
    RecoveryState,
)
from app.incident_response.triage import IncidentTriageEngine, incident_triage_engine

logger = logging.getLogger(__name__)


class IncidentResponseEngine:
    """Orchestrates the entire operational incident response loop from detection to verified recovery and learning.

    Invariant 1: Situation != Incident != Symptom != Hypothesis != Cause != Mitigation != Recovery.
    Invariant 8: Execution != Verification. Resolution requires verified recovery evidence.
    Invariant 21: Root cause may remain unknown; ROOT_CAUSE_UNKNOWN is a valid outcome.
    """

    def __init__(
        self,
        triage_eng: IncidentTriageEngine | None = None,
        investigation_eng: InvestigationEngine | None = None,
        hypotheses_mgr: HypothesisManager | None = None,
        options_eng: ResponseOptionEngine | None = None,
        mitigation_eng: MitigationEngine | None = None,
        recovery_eng: Any | None = None,
        checkpoint_mgr: CheckpointManager | None = None,
        reconciler: IncidentReconciler | None = None,
        postmortem_eng: PostmortemEngine | None = None,
        learning_eng: IncidentLearningEngine | None = None,
        auditor: IncidentAuditor | None = None,
    ) -> None:
        self.triage_engine = triage_eng or incident_triage_engine
        self.investigation_engine = investigation_eng or investigation_engine
        self.hypotheses_manager = hypotheses_mgr or hypothesis_manager
        self.options_engine = options_eng or response_option_engine
        self.mitigation_engine = mitigation_eng or mitigation_engine
        self.recovery_engine = recovery_eng or recovery_engine
        self.checkpoint_manager = checkpoint_mgr or checkpoint_manager
        self.reconciler = reconciler or incident_reconciler
        self.postmortem_engine = postmortem_eng or postmortem_engine
        self.learning_engine = learning_eng or incident_learning_engine
        self.auditor = auditor or incident_auditor

        # In-memory incident store
        self._incidents: dict[str, IncidentResponse] = {}

    def create_incident_from_situation(
        self,
        situation: dict[str, Any],
        actor: str = "SYSTEM",
        active_plans: list[dict[str, Any]] | None = None,
        active_goals: list[dict[str, Any]] | None = None,
        available_capabilities: list[str] | None = None,
    ) -> IncidentResponse:
        """Initialize an operational incident from an existing situational awareness situation."""
        sit_id = situation.get("situation_id")
        raw_title = situation.get("title", f"Incident on {situation.get('affected_resources', ['system'])}")
        clean_title = sanitize_incident_directive(raw_title)

        # 1. Triage severity & urgency
        triage = self.triage_engine.triage_situation(
            situation=situation,
            active_plans=active_plans,
            active_goals=active_goals,
        )

        inc_id = f"inc_{uuid.uuid4().hex[:8]}"

        # 2. Hypotheses initialization
        raw_hyps = situation.get("hypotheses", [])
        hyps = self.hypotheses_manager.initialize_hypotheses(
            raw_hypotheses=[h if isinstance(h, dict) else h.model_dump() for h in raw_hyps],
            affected_resources=situation.get("affected_resources", []),
        )

        # 3. Build Investigation Plan
        inv_plan = self.investigation_engine.build_investigation_plan(
            incident_id=inc_id,
            affected_resources=situation.get("affected_resources", []),
            hypotheses=hyps,
        )

        # 4. Generate Response Options
        leading_cause = hyps[0].candidate_cause if hyps else None
        options = self.options_engine.generate_options(
            incident_id=inc_id,
            severity=triage["severity"],
            affected_resources=situation.get("affected_resources", []),
            leading_cause=leading_cause,
            available_capabilities=available_capabilities,
        )

        now = datetime.now(timezone.utc)
        timeline = [
            {
                "timestamp": now.isoformat(),
                "event": "INCIDENT_CREATED",
                "summary": f"Incident initialized from situation {sit_id}. Severity: {triage['severity'].value}",
            }
        ]

        incident = IncidentResponse(
            response_id=f"ir_{uuid.uuid4().hex[:10]}",
            incident_id=inc_id,
            situation_id=sit_id,
            title=clean_title,
            description=situation.get("description", ""),
            status=IncidentStatus.INVESTIGATING,
            severity=triage["severity"],
            urgency=triage["urgency"],
            environment=situation.get("environment", "development"),
            confidence=triage["confidence"],
            affected_resources=situation.get("affected_resources", []),
            affected_services=situation.get("affected_services", []),
            affected_plans=situation.get("affected_plans", []),
            affected_goals=situation.get("affected_goals", []),
            incident_commander=actor if triage["requires_commander"] else None,
            hypotheses=hyps,
            investigation=inv_plan,
            response_options=options,
            automation_level=triage["automation_level"],
            timeline=timeline,
            provenance={"created_by": actor, "situation_id": sit_id},
            created_at=now,
            updated_at=now,
        )

        self._incidents[inc_id] = incident
        self.auditor.record_event(
            event_type="INCIDENT_CREATED",
            actor=actor,
            incident_id=inc_id,
            details={"title": clean_title, "severity": triage["severity"].value, "situation_id": sit_id},
        )

        logger.info(
            "INCIDENT_INITIALIZED: id=%s title='%s' sev=%s", inc_id, clean_title, triage["severity"].value
        )
        return incident

    def get_incident(self, incident_id: str) -> IncidentResponse:
        """Retrieve an active incident by ID."""
        inc = self._incidents.get(incident_id)
        if not inc:
            raise IncidentResponseSafetyError(f"Incident '{incident_id}' not found.")
        return inc

    def list_incidents(
        self,
        environment: str | None = None,
        status: IncidentStatus | None = None,
    ) -> list[IncidentResponse]:
        """List active and historical incidents."""
        results = list(self._incidents.values())
        if environment:
            results = [i for i in results if i.environment.lower() == environment.lower()]
        if status:
            results = [i for i in results if i.status == status]
        return results

    def triage_incident(
        self,
        incident_id: str,
        override_severity: IncidentSeverity | None = None,
        override_urgency: IncidentUrgency | None = None,
        actor: str = "SYSTEM_USER",
        reason: str = "Manual triage override",
    ) -> IncidentResponse:
        """Apply authorized triage adjustments to severity and urgency."""
        inc = self.get_incident(incident_id)
        if override_severity:
            inc.severity = override_severity
        if override_urgency:
            inc.urgency = override_urgency

        inc.updated_at = datetime.now(timezone.utc)
        inc.timeline.append(
            {
                "timestamp": inc.updated_at.isoformat(),
                "event": "INCIDENT_TRIAGED",
                "summary": f"Triage updated by {actor}: sev={inc.severity.value}, urg={inc.urgency.value}. Reason: {reason}",
            }
        )

        self.auditor.record_event(
            event_type="INCIDENT_TRIAGED",
            actor=actor,
            incident_id=incident_id,
            details={"severity": inc.severity.value, "urgency": inc.urgency.value, "reason": reason},
        )
        return inc

    def add_evidence(
        self,
        incident_id: str,
        hypothesis_id: str,
        evidence: EvidenceItem,
        is_supporting: bool,
        actor: str = "INVESTIGATOR",
    ) -> IncidentResponse:
        """Add supporting or contradictory evidence to a candidate hypothesis."""
        inc = self.get_incident(incident_id)
        updated_hyp = self.hypotheses_manager.add_evidence(
            hypotheses=inc.hypotheses,
            hypothesis_id=hypothesis_id,
            evidence=evidence,
            is_supporting=is_supporting,
        )
        if not updated_hyp:
            raise IncidentResponseSafetyError(
                f"Hypothesis '{hypothesis_id}' not found in incident '{incident_id}'."
            )

        inc.updated_at = datetime.now(timezone.utc)
        inc.timeline.append(
            {
                "timestamp": inc.updated_at.isoformat(),
                "event": "EVIDENCE_ADDED",
                "summary": f"Evidence added to hypothesis '{updated_hyp.candidate_cause[:30]}' (supporting={is_supporting}).",
            }
        )

        self.auditor.record_event(
            event_type="EVIDENCE_ADDED",
            actor=actor,
            incident_id=incident_id,
            details={
                "hypothesis_id": hypothesis_id,
                "is_supporting": is_supporting,
                "new_status": updated_hyp.status.value,
            },
        )
        return inc

    def select_response_option(
        self,
        incident_id: str,
        option_id: str,
        actor: str = "INCIDENT_COMMANDER",
    ) -> IncidentResponse:
        """Select response strategy, generate mitigation/recovery action, and route for approval or execution."""
        inc = self.get_incident(incident_id)
        opt = next((o for o in inc.response_options if o.option_id == option_id), None)
        if not opt:
            raise IncidentResponseSafetyError(
                f"Response option '{option_id}' not found in incident '{incident_id}'."
            )

        inc.selected_option_id = option_id
        action = self.mitigation_engine.prepare_mitigation_action(
            incident_id=incident_id,
            option=opt,
            actor=actor,
        )
        inc.actions.append(action)

        target_res = inc.affected_resources[0] if inc.affected_resources else "system"
        inc.recovery_plan = self.recovery_engine.build_recovery_plan(
            incident_id=incident_id,
            strategy=opt.strategy_type,
            target_resource=target_res,
        )

        if action.requires_approval:
            inc.status = IncidentStatus.AWAITING_APPROVAL
        else:
            inc.status = IncidentStatus.MITIGATING

        inc.updated_at = datetime.now(timezone.utc)
        inc.timeline.append(
            {
                "timestamp": inc.updated_at.isoformat(),
                "event": "OPTION_SELECTED",
                "summary": f"Selected response '{opt.title}'. Status: {inc.status.value}",
            }
        )

        self.auditor.record_event(
            event_type="OPTION_SELECTED",
            actor=actor,
            incident_id=incident_id,
            details={"option_id": option_id, "strategy": opt.strategy_type, "status": inc.status.value},
        )
        return inc

    def approve_action(
        self,
        incident_id: str,
        action_id: str,
        approver: str,
        reason: str = "Approved by commander",
    ) -> IncidentResponse:
        """Approve a pending high-impact action, checking separation of duties."""
        inc = self.get_incident(incident_id)
        action = next((a for a in inc.actions if a.action_id == action_id), None)
        if not action:
            raise IncidentResponseSafetyError(f"Action '{action_id}' not found in incident '{incident_id}'.")

        # Invariant 63: Separation of duties on critical incidents
        verify_separation_of_duties(
            investigator=inc.incident_commander or "investigator",
            decision_maker=approver,
            executor="operator",
            verifier="verifier",
            is_critical=inc.severity == IncidentSeverity.CRITICAL,
        )

        action.status = ActionState.APPROVED
        inc.status = IncidentStatus.MITIGATING
        if inc.recovery_plan:
            inc.recovery_plan.status = RecoveryState.IN_PROGRESS
        inc.updated_at = datetime.now(timezone.utc)
        inc.timeline.append(
            {
                "timestamp": inc.updated_at.isoformat(),
                "event": "ACTION_APPROVED",
                "summary": f"Action '{action.title}' approved by {approver}. Reason: {reason}",
            }
        )

        self.auditor.record_event(
            event_type="ACTION_APPROVED",
            actor=approver,
            incident_id=incident_id,
            details={"action_id": action_id, "reason": reason},
        )
        return inc

    def verify_recovery_checkpoint(
        self,
        incident_id: str,
        checkpoint_id: str,
        verifier: str,
        verification_evidence: dict[str, Any],
        environmental_drift: bool = False,
    ) -> IncidentResponse:
        """Validate recovery checkpoint barrier."""
        inc = self.get_incident(incident_id)
        if not inc.recovery_plan:
            raise IncidentResponseSafetyError(f"No active recovery plan for incident '{incident_id}'.")

        passed, msg = self.checkpoint_manager.verify_checkpoint(
            plan=inc.recovery_plan,
            checkpoint_id=checkpoint_id,
            verification_evidence=verification_evidence,
            environmental_drift=environmental_drift,
        )

        if not passed:
            raise IncidentResponseSafetyError(f"Checkpoint verification failed: {msg}")

        if inc.recovery_plan.status == RecoveryState.RECOVERED:
            inc.status = IncidentStatus.VERIFYING
        else:
            inc.status = IncidentStatus.RECOVERING

        inc.updated_at = datetime.now(timezone.utc)
        inc.timeline.append(
            {
                "timestamp": inc.updated_at.isoformat(),
                "event": "CHECKPOINT_VERIFIED",
                "summary": f"Recovery checkpoint {checkpoint_id} verified by {verifier}: {msg}",
            }
        )

        self.auditor.record_event(
            event_type="CHECKPOINT_VERIFIED",
            actor=verifier,
            incident_id=incident_id,
            details={
                "checkpoint_id": checkpoint_id,
                "message": msg,
                "plan_status": inc.recovery_plan.status.value,
            },
        )
        return inc

    def resolve_incident(
        self,
        incident_id: str,
        actor: str,
        verification_evidence: dict[str, Any],
        resolution_notes: str = "",
    ) -> IncidentResponse:
        """Resolve incident only upon verified recovery evidence.

        Invariant 8 & 10 & 28: Silence != Recovery. Alerts stopping is not sufficient to resolve.
        """
        inc = self.get_incident(incident_id)

        # Invariant: False recovery defense
        if not verification_evidence or not verification_evidence.get("is_verified", False):
            raise IncidentResponseSafetyError(
                f"False Recovery Defense: Incident '{incident_id}' cannot be resolved without verified evidence."
            )

        now = datetime.now(timezone.utc)
        inc.status = IncidentStatus.RESOLVED
        inc.resolved_at = now
        inc.updated_at = now

        # Generate blameless postmortem
        pm = self.postmortem_engine.generate_postmortem(inc)
        inc.postmortem = pm

        # Dispatch cross-engine learning
        self.learning_engine.dispatch_learnings(inc, pm)

        inc.timeline.append(
            {
                "timestamp": now.isoformat(),
                "event": "INCIDENT_RESOLVED",
                "summary": f"Incident resolved by {actor}. Notes: {resolution_notes}",
            }
        )

        self.auditor.record_event(
            event_type="INCIDENT_RESOLVED",
            actor=actor,
            incident_id=incident_id,
            details={"verification_evidence": verification_evidence, "notes": resolution_notes},
        )

        logger.info("INCIDENT_RESOLVED: id=%s by=%s", incident_id, actor)
        return inc

    def reopen_incident(
        self,
        incident_id: str,
        actor: str,
        reason: str = "Recurrence detected",
    ) -> IncidentResponse:
        """Reopen previously resolved incident upon symptom recurrence."""
        inc = self.get_incident(incident_id)
        now = datetime.now(timezone.utc)
        inc.status = IncidentStatus.INVESTIGATING
        inc.resolved_at = None
        inc.updated_at = now

        inc.timeline.append(
            {
                "timestamp": now.isoformat(),
                "event": "INCIDENT_REOPENED",
                "summary": f"Incident reopened by {actor}. Reason: {reason}",
            }
        )

        self.auditor.record_event(
            event_type="INCIDENT_REOPENED",
            actor=actor,
            incident_id=incident_id,
            details={"reason": reason},
        )

        logger.warning("INCIDENT_REOPENED: id=%s by=%s reason='%s'", incident_id, actor, reason)
        return inc


incident_response_engine = IncidentResponseEngine()
