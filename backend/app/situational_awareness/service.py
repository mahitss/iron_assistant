"""Transactional facade service managing persistence and lifecycle of situations (Task 60)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.situational_awareness.engine import (
    SituationalAwarenessEngine,
    situational_awareness_engine,
)
from app.situational_awareness.models import (
    NormalizedEventModel,
    SituationModel,
)
from app.situational_awareness.safety import SituationalAwarenessSafetyError
from app.situational_awareness.schemas import (
    AttentionItem,
    EventIngestRequest,
    SignalBaseline,
    Situation,
    SituationSeverity,
    SituationStatus,
    SituationTimelineEntry,
)

logger = logging.getLogger(__name__)


class SituationalAwarenessService:
    """Service facade coordinating engine domain logic with database transactions."""

    def __init__(self, engine: SituationalAwarenessEngine | None = None) -> None:
        self._engine = engine or situational_awareness_engine

    async def ingest_event(
        self,
        request: EventIngestRequest,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Ingest event, run correlation and situation synthesis."""
        result = self._engine.process_event(request)

        if db and result.get("status") == "PROCESSED":
            evt_id = result["event_id"]
            evt = self._engine._events.get(evt_id)
            if evt:
                evt_model = NormalizedEventModel(
                    event_id=evt.event_id,
                    situation_id=evt.situation_id,
                    event_type=evt.event_type,
                    source=evt.source,
                    source_trust=evt.source_trust.value,
                    environment=evt.environment,
                    resource=evt.resource,
                    subject=evt.subject,
                    actor=evt.actor,
                    payload=evt.payload,
                    severity=evt.severity.value,
                    confidence=evt.confidence,
                    provenance=evt.provenance,
                    correlation_id=evt.correlation_id,
                    causation_id=evt.causation_id,
                    is_anomaly=evt.is_anomaly,
                    occurred_at=evt.occurred_at,
                    received_at=evt.received_at,
                )
                db.add(evt_model)

                # Persist or update SituationModel
                sit_id = result["situation_id"]
                sit = self._engine._situations.get(sit_id)
                if sit:
                    sit_res = await db.execute(
                        select(SituationModel).where(SituationModel.situation_id == sit_id)
                    )
                    sit_model = sit_res.scalar_one_or_none()
                    if not sit_model:
                        sit_model = SituationModel(
                            situation_id=sit.situation_id,
                            title=sit.title,
                            description=sit.description,
                            status=sit.status.value,
                            severity=sit.severity.value,
                            confidence=sit.confidence,
                            environment=sit.environment,
                            affected_resources=sit.affected_resources,
                            affected_services=sit.affected_services,
                            affected_plans=sit.affected_plans,
                            affected_goals=sit.affected_goals,
                            current_state=sit.current_state,
                            expected_state=sit.expected_state,
                            timeline=[e.model_dump() for e in sit.timeline],
                            evidence=sit.evidence,
                            risk_assessment=sit.risk_assessment,
                            next_steps=sit.next_steps,
                            provenance=sit.provenance,
                            flapping_count=sit.flapping_count,
                            last_observed_at=sit.last_observed_at,
                        )
                        db.add(sit_model)
                    else:
                        sit_model.severity = sit.severity.value
                        sit_model.status = sit.status.value
                        sit_model.affected_resources = sit.affected_resources
                        sit_model.affected_services = sit.affected_services
                        sit_model.affected_plans = sit.affected_plans
                        sit_model.timeline = [e.model_dump() for e in sit.timeline]
                        sit_model.last_observed_at = sit.last_observed_at

                await db.commit()

        return result

    async def get_situation(self, situation_id: str, db: AsyncSession | None = None) -> Situation:
        """Fetch situation by ID."""
        if db:
            res = await db.execute(select(SituationModel).where(SituationModel.situation_id == situation_id))
            model = res.scalar_one_or_none()
            if model:
                timeline_entries = [SituationTimelineEntry(**e) for e in model.timeline]
                return Situation(
                    situation_id=model.situation_id,
                    title=model.title,
                    description=model.description,
                    status=SituationStatus(model.status),
                    severity=SituationSeverity(model.severity),
                    confidence=model.confidence,
                    environment=model.environment,
                    affected_resources=model.affected_resources,
                    affected_services=model.affected_services,
                    affected_plans=model.affected_plans,
                    affected_goals=model.affected_goals,
                    current_state=model.current_state,
                    expected_state=model.expected_state,
                    timeline=timeline_entries,
                    evidence=model.evidence,
                    risk_assessment=model.risk_assessment,
                    next_steps=model.next_steps,
                    provenance=model.provenance,
                    flapping_count=model.flapping_count,
                    last_observed_at=model.last_observed_at,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                )

        sit = self._engine._situations.get(situation_id)
        if not sit:
            raise SituationalAwarenessSafetyError(f"Situation '{situation_id}' not found.")
        return sit

    async def list_situations(
        self,
        environment: str | None = None,
        status: SituationStatus | None = None,
        db: AsyncSession | None = None,
    ) -> list[Situation]:
        """List active or historical situations."""
        results = list(self._engine._situations.values())
        if environment:
            results = [s for s in results if s.environment.lower() == environment.lower()]
        if status:
            results = [s for s in results if s.status == status]
        return results

    async def resolve_situation(
        self,
        situation_id: str,
        actor: str,
        verification_evidence: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> Situation:
        """Resolve situation with verification evidence."""
        sit = self._engine.resolve_situation(situation_id, actor, verification_evidence)
        if db:
            res = await db.execute(select(SituationModel).where(SituationModel.situation_id == situation_id))
            model = res.scalar_one_or_none()
            if model:
                model.status = sit.status.value
                await db.commit()
        return sit

    def get_attention_feed(self) -> list[AttentionItem]:
        """Retrieve ranked attention feed."""
        return self._engine.get_attention_feed()

    def get_baselines(self, environment: str | None = None) -> list[SignalBaseline]:
        """List operational baselines."""
        return self._engine.baselines.list_baselines(environment=environment)

    def get_audit_trail(self, situation_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve audit events."""
        return self._engine.auditor.get_events(situation_id=situation_id, limit=limit)


situational_awareness_service = SituationalAwarenessService()
