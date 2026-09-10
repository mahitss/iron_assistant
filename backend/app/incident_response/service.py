"""Transactional facade service managing persistence and lifecycle of incident responses (Task 61)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.incident_response.engine import IncidentResponseEngine, incident_response_engine
from app.incident_response.models import (
    IncidentResponseModel,
)
from app.incident_response.schemas import (
    AddEvidenceRequest,
    ApproveActionRequest,
    CreateIncidentFromSituationRequest,
    EvidenceItem,
    IncidentResponse,
    IncidentStatus,
    ResolveIncidentRequest,
    TriageIncidentRequest,
    VerifyRecoveryRequest,
)

logger = logging.getLogger(__name__)


class IncidentResponseService:
    """Service facade coordinating engine domain logic with database transactions."""

    def __init__(self, engine: IncidentResponseEngine | None = None) -> None:
        self._engine = engine or incident_response_engine

    async def create_incident_from_situation(
        self,
        req: CreateIncidentFromSituationRequest,
        situation_data: dict[str, Any] | None = None,
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Create and initialize an incident from a situation."""
        sit_payload = situation_data or {
            "situation_id": req.situation_id,
            "title": req.title or f"Incident for situation {req.situation_id}",
            "description": req.description,
            "environment": req.environment,
            "affected_resources": req.affected_resources or ["production-api"],
            "affected_services": req.affected_services or [],
            "severity": "HIGH",
            "context": req.context,
        }

        incident = self._engine.create_incident_from_situation(
            situation=sit_payload,
            actor=req.actor,
        )

        if db:
            model = IncidentResponseModel(
                response_id=incident.response_id,
                incident_id=incident.incident_id,
                situation_id=incident.situation_id,
                title=incident.title,
                description=incident.description,
                status=incident.status.value,
                severity=incident.severity.value,
                urgency=incident.urgency.value,
                environment=incident.environment,
                confidence=incident.confidence,
                affected_resources=incident.affected_resources,
                affected_services=incident.affected_services,
                affected_plans=incident.affected_plans,
                affected_goals=incident.affected_goals,
                responders=incident.responders,
                incident_commander=incident.incident_commander,
                automation_level=incident.automation_level.value,
                timeline=incident.timeline,
                provenance=incident.provenance,
            )
            db.add(model)
            await db.commit()

        return incident

    async def get_incident(
        self,
        incident_id: str,
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Retrieve an incident by ID."""
        return self._engine.get_incident(incident_id)

    async def list_incidents(
        self,
        environment: str | None = None,
        status: IncidentStatus | None = None,
        db: AsyncSession | None = None,
    ) -> list[IncidentResponse]:
        """List active and historical incidents."""
        return self._engine.list_incidents(environment=environment, status=status)

    async def triage_incident(
        self,
        incident_id: str,
        req: TriageIncidentRequest,
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Triage an incident adjusting severity and urgency."""
        severity = req.override_severity or req.severity
        urgency = req.override_urgency or req.urgency
        actor = req.responder or req.actor
        reason = req.triage_notes or req.reason
        return self._engine.triage_incident(
            incident_id=incident_id,
            override_severity=severity,
            override_urgency=urgency,
            actor=actor,
            reason=reason,
        )

    async def add_evidence(
        self,
        incident_id: str,
        req: AddEvidenceRequest,
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Attach supporting or contradictory evidence to a candidate hypothesis."""
        is_supporting = req.supports if req.supports is not None else req.is_supporting
        details = req.details or req.raw_data or {}
        if req.summary and "summary" not in details:
            details["summary"] = req.summary
        evidence = EvidenceItem(
            source=req.source,
            trust_level="TRUSTED_SYSTEM",
            relevance_score=req.relevance,
            is_verified=req.is_verified,
            details=details,
        )
        return self._engine.add_evidence(
            incident_id=incident_id,
            hypothesis_id=req.hypothesis_id,
            evidence=evidence,
            is_supporting=is_supporting,
        )

    async def select_option(
        self,
        incident_id: str,
        option_id: str,
        actor: str = "INCIDENT_COMMANDER",
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Select a candidate mitigation or recovery strategy."""
        return self._engine.select_response_option(
            incident_id=incident_id,
            option_id=option_id,
            actor=actor,
        )

    async def approve_action(
        self,
        incident_id: str,
        req: ApproveActionRequest,
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Approve a pending high-impact action."""
        reason = req.approval_notes or req.reason
        return self._engine.approve_action(
            incident_id=incident_id,
            action_id=req.action_id,
            approver=req.approver,
            reason=reason,
        )

    async def verify_checkpoint(
        self,
        incident_id: str,
        req: VerifyRecoveryRequest,
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Validate recovery checkpoint barrier."""
        evidence = dict(req.verification_evidence) if req.verification_evidence else {}
        evidence["is_verified"] = req.is_verified
        if req.observed_metrics:
            evidence["observed_metrics"] = req.observed_metrics
        if req.notes:
            evidence["notes"] = req.notes
        return self._engine.verify_recovery_checkpoint(
            incident_id=incident_id,
            checkpoint_id=req.checkpoint_id,
            verifier=req.verifier,
            verification_evidence=evidence,
        )

    async def resolve_incident(
        self,
        incident_id: str,
        req: ResolveIncidentRequest,
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Resolve incident with verified evidence and generate postmortem."""
        actor = req.resolver or req.actor
        evidence = dict(req.verification_evidence) if req.verification_evidence else {}
        if not req.is_verified:
            evidence["is_verified"] = False
        elif "is_verified" not in evidence:
            evidence["is_verified"] = True
        if req.verification_notes:
            evidence["verification_notes"] = req.verification_notes
        notes = req.resolution_summary or req.resolution_notes
        return self._engine.resolve_incident(
            incident_id=incident_id,
            actor=actor,
            verification_evidence=evidence,
            resolution_notes=notes,
        )

    async def reopen_incident(
        self,
        incident_id: str,
        actor: str = "SYSTEM_USER",
        reason: str = "Recurring symptoms detected",
        db: AsyncSession | None = None,
    ) -> IncidentResponse:
        """Reopen a resolved incident."""
        return self._engine.reopen_incident(
            incident_id=incident_id,
            actor=actor,
            reason=reason,
        )

    def get_audit_trail(
        self,
        incident_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve audit trail records."""
        return self._engine.auditor.get_events(incident_id=incident_id, limit=limit)


incident_response_service = IncidentResponseService()
