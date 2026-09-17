"""Transactional facade service managing persistence, lifecycle, and query operations for situations (Task 60 & Task 99)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.situational_awareness.domain import (
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
)
from app.situational_awareness.engine import (
    SituationalAwarenessEngine,
    situational_awareness_engine,
)
from app.situational_awareness.models import (
    NormalizedEventModel,
    SignalModel,
    SituationContextModel,
    SituationInterventionModel,
    SituationModel,
    SituationPatternModel,
    SituationSuppressionModel,
)
from app.situational_awareness.safety import SituationalAwarenessSafetyError
from app.situational_awareness.schemas import (
    AttentionItem,
    EventIngestRequest,
    SignalBaseline,
    Situation,
    SituationStatus,
)

logger = logging.getLogger("kairo.situational_awareness.service")


class SituationalAwarenessService:
    """Service facade coordinating engine domain logic with database transactions."""

    def __init__(self, engine: SituationalAwarenessEngine | None = None) -> None:
        self._engine = engine or situational_awareness_engine

    async def ingest_signal(
        self,
        signal: SignalRecord,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Ingest canonical signal into situational awareness engine and persist state."""
        result = self._engine.process_signal(signal)

        if db and result.get("status") == "PROCESSED":
            sig_model = SignalModel(
                signal_id=signal.signal_id,
                situation_id=result.get("situation_id"),
                source_type=signal.source_type,
                source_id=signal.source_id,
                source_version=signal.source_version,
                observed_at=signal.observed_at,
                received_at=signal.received_at,
                effective_at=signal.effective_at,
                signal_type=signal.signal_type,
                subject=signal.subject,
                entity=signal.entity,
                scope=signal.scope,
                payload_ref=signal.payload_ref,
                payload=signal.payload,
                confidence=signal.confidence,
                freshness=signal.freshness,
                trust_classification=signal.trust_classification.value if hasattr(signal.trust_classification, "value") else str(signal.trust_classification),
                sensitivity_classification=signal.sensitivity_classification.value if hasattr(signal.sensitivity_classification, "value") else str(signal.sensitivity_classification),
                correlation_keys=signal.correlation_keys,
                causal_references=signal.causal_references,
                world_state_references=signal.world_state_references,
                decision_action_references=signal.decision_action_references,
                trace_id=signal.trace_id,
                correlation_id=signal.correlation_id,
                event_id=signal.event_id,
                metadata_json=signal.metadata,
            )
            db.add(sig_model)

            sit_id = result["situation_id"]
            sit = self._engine._situations.get(sit_id)
            if sit:
                await self._persist_or_update_situation(sit, db)

            await db.commit()

        return result

    async def ingest_event(
        self,
        request: EventIngestRequest,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Backward-compatible Task 60 event ingestion."""
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
                    source_trust=evt.source_trust.value if hasattr(evt.source_trust, "value") else str(evt.source_trust),
                    environment=evt.environment,
                    resource=evt.resource,
                    subject=evt.subject,
                    actor=evt.actor,
                    payload=evt.payload,
                    severity=evt.severity.value if hasattr(evt.severity, "value") else str(evt.severity),
                    confidence=evt.confidence,
                    provenance=evt.provenance,
                    correlation_id=evt.correlation_id,
                    causation_id=evt.causation_id,
                    is_anomaly=evt.is_anomaly,
                    occurred_at=evt.occurred_at,
                    received_at=evt.received_at,
                )
                db.add(evt_model)

                sit_id = result["situation_id"]
                sit = self._engine._situations.get(sit_id)
                if sit:
                    await self._persist_or_update_situation(sit, db)

                await db.commit()

        return result

    async def _persist_or_update_situation(self, sit: SituationRecord, db: AsyncSession) -> None:
        """Helper to upsert situation record in database."""
        sit_res = await db.execute(
            select(SituationModel).where(SituationModel.situation_id == sit.id)
        )
        model = sit_res.scalar_one_or_none()
        timeline_dicts = [e.to_dict() for e in sit.timeline]

        if not model:
            model = SituationModel(
                situation_id=sit.id,
                tenant_id=sit.tenant_id,
                user_id=sit.user_id,
                project_id=sit.project_id,
                situation_type=sit.situation_type.value,
                status=sit.lifecycle_state.value,
                lifecycle_state=sit.lifecycle_state.value,
                title=sit.title,
                description=sit.summary,
                summary=sit.summary,
                created_at=sit.created_at,
                updated_at=sit.updated_at,
                first_signal_at=sit.first_signal_at,
                last_signal_at=sit.last_signal_at,
                last_observed_at=sit.last_observed_at,
                resolved_at=sit.resolved_at,
                expires_at=sit.expires_at,
                severity=sit.severity.value,
                priority=sit.priority,
                confidence=sit.confidence,
                novelty=sit.novelty,
                urgency=sit.urgency,
                impact_score=sit.impact,
                uncertainty=sit.uncertainty,
                observability_quality=sit.observability_quality,
                freshness=sit.freshness,
                environment="production" if sit.tenant_id == "production" else "development",
                affected_entities=sit.affected_entities,
                affected_capabilities=sit.affected_capabilities,
                affected_resources=sit.affected_resources,
                affected_goals=sit.affected_goals,
                affected_workflows=sit.affected_workflows,
                affected_agents=sit.affected_agents,
                affected_projects=sit.affected_projects,
                affected_services=sit.affected_services,
                affected_plans=[],
                source_count=sit.source_count,
                signal_count=sit.signal_count,
                correlation_score=sit.correlation_score,
                duplicate_group=sit.duplicate_group,
                parent_situation_id=sit.parent_situation_id,
                supersedes_situation_id=sit.supersedes_situation_id,
                merged_from_ids=sit.merged_from_ids,
                merged_into_id=sit.merged_into_id,
                split_from_id=sit.split_from_id,
                causal_status=sit.causal_status.value,
                state_reconciliation_status=sit.state_reconciliation_status.value,
                recommended_next_step=sit.recommended_next_step,
                current_decision_id=sit.current_decision_id,
                current_action_transaction_id=sit.current_action_transaction_id,
                timeline=timeline_dicts,
                evidence=sit.evidence,
                risk_assessment={},
                next_steps=[sit.recommended_next_step] if sit.recommended_next_step else [],
                provenance={"source_count": sit.source_count},
                flapping_count=0,
                version=sit.version,
                metadata_json=sit.metadata,
            )
            db.add(model)
        else:
            model.status = sit.lifecycle_state.value
            model.lifecycle_state = sit.lifecycle_state.value
            model.severity = sit.severity.value
            model.priority = sit.priority
            model.confidence = sit.confidence
            model.urgency = sit.urgency
            model.signal_count = sit.signal_count
            model.last_signal_at = sit.last_signal_at
            model.last_observed_at = sit.last_observed_at
            model.resolved_at = sit.resolved_at
            model.affected_entities = sit.affected_entities
            model.affected_resources = sit.affected_resources
            model.timeline = timeline_dicts
            model.causal_status = sit.causal_status.value
            model.state_reconciliation_status = sit.state_reconciliation_status.value
            model.current_decision_id = sit.current_decision_id
            model.current_action_transaction_id = sit.current_action_transaction_id
            model.version = sit.version
            model.updated_at = sit.updated_at

    async def get_situation(self, situation_id: str, db: AsyncSession | None = None) -> SituationRecord:
        """Retrieve situation by ID, checking database if provided."""
        if db:
            res = await db.execute(select(SituationModel).where(SituationModel.situation_id == situation_id))
            model = res.scalar_one_or_none()
            if model:
                # Reconstruct domain SituationRecord
                return SituationRecord(
                    id=model.situation_id,
                    tenant_id=model.tenant_id or "default",
                    user_id=model.user_id,
                    project_id=model.project_id,
                    situation_type=SituationType(model.situation_type) if hasattr(SituationType, model.situation_type) else SituationType.INCIDENT,
                    lifecycle_state=SituationLifecycleState(model.lifecycle_state) if hasattr(SituationLifecycleState, model.lifecycle_state) else SituationLifecycleState.DETECTED,
                    title=model.title,
                    summary=model.summary or model.description,
                    created_at=model.created_at,
                    updated_at=model.updated_at,
                    first_signal_at=model.first_signal_at,
                    last_signal_at=model.last_signal_at,
                    last_observed_at=model.last_observed_at,
                    resolved_at=model.resolved_at,
                    expires_at=model.expires_at,
                    severity=SituationSeverity(model.severity) if hasattr(SituationSeverity, model.severity) else SituationSeverity.MEDIUM,
                    priority=model.priority,
                    confidence=model.confidence,
                    novelty=model.novelty,
                    urgency=model.urgency,
                    impact=model.impact_score,
                    uncertainty=model.uncertainty,
                    observability_quality=model.observability_quality,
                    freshness=model.freshness,
                    affected_entities=model.affected_entities or [],
                    affected_capabilities=model.affected_capabilities or [],
                    affected_resources=model.affected_resources or [],
                    affected_goals=model.affected_goals or [],
                    affected_workflows=model.affected_workflows or [],
                    affected_agents=model.affected_agents or [],
                    affected_projects=model.affected_projects or [],
                    affected_services=model.affected_services or [],
                    source_count=model.source_count,
                    signal_count=model.signal_count,
                    correlation_score=model.correlation_score,
                    duplicate_group=model.duplicate_group,
                    parent_situation_id=model.parent_situation_id,
                    supersedes_situation_id=model.supersedes_situation_id,
                    merged_from_ids=model.merged_from_ids or [],
                    merged_into_id=model.merged_into_id,
                    split_from_id=model.split_from_id,
                    causal_status=CausalStatus(model.causal_status) if hasattr(CausalStatus, model.causal_status) else CausalStatus.CORRELATED,
                    state_reconciliation_status=StateReconciliationStatus(model.state_reconciliation_status) if hasattr(StateReconciliationStatus, model.state_reconciliation_status) else StateReconciliationStatus.UNVERIFIED,
                    recommended_next_step=model.recommended_next_step,
                    current_decision_id=model.current_decision_id,
                    current_action_transaction_id=model.current_action_transaction_id,
                    version=model.version,
                    metadata=model.metadata_json or {},
                    evidence=model.evidence or [],
                )

        sit = self._engine._situations.get(situation_id)
        if not sit:
            raise SituationalAwarenessSafetyError(f"Situation '{situation_id}' not found.")
        return sit

    async def list_situations(
        self,
        tenant_id: str | None = None,
        project_id: str | None = None,
        lifecycle_state: SituationLifecycleState | None = None,
        situation_type: SituationType | None = None,
        severity: SituationSeverity | None = None,
        limit: int = 50,
        offset: int = 0,
        db: AsyncSession | None = None,
    ) -> list[SituationRecord]:
        """List situations matching filtering criteria."""
        results = list(self._engine._situations.values())
        if tenant_id:
            results = [s for s in results if s.tenant_id == tenant_id]
        if project_id:
            results = [s for s in results if s.project_id == project_id]
        if lifecycle_state:
            results = [s for s in results if s.lifecycle_state == lifecycle_state]
        if situation_type:
            results = [s for s in results if s.situation_type == situation_type]
        if severity:
            results = [s for s in results if s.severity == severity]

        results.sort(key=lambda s: s.updated_at, reverse=True)
        return results[offset : offset + limit]

    async def resolve_situation(
        self,
        situation_id: str,
        actor: str,
        verification_evidence: dict[str, Any],
        db: AsyncSession | None = None,
    ) -> SituationRecord:
        """Resolve situation with empirical verification."""
        sit = self._engine.resolve_situation(situation_id, actor, verification_evidence)
        if db:
            await self._persist_or_update_situation(sit, db)
            await db.commit()
        return sit

    async def suppress_situation(
        self,
        situation_id: str,
        suppressed_by: str,
        reason: str,
        duration_seconds: int = 3600,
        db: AsyncSession | None = None,
    ) -> SituationSuppressionRecord:
        """Suppress situation with audit record."""
        record = self._engine.suppress_situation(situation_id, suppressed_by, reason, duration_seconds)
        if db:
            supp_model = SituationSuppressionModel(
                suppression_id=record.suppression_id,
                situation_id=record.situation_id,
                suppressed_by=record.suppressed_by,
                reason=record.reason,
                duration_seconds=record.duration_seconds,
                expires_at=record.expires_at,
                is_active=record.is_active,
                created_at=record.created_at,
            )
            db.add(supp_model)
            sit = self._engine._situations.get(situation_id)
            if sit:
                await self._persist_or_update_situation(sit, db)
            await db.commit()
        return record

    async def reopen_situation(
        self,
        situation_id: str,
        actor: str,
        reason: str,
        db: AsyncSession | None = None,
    ) -> SituationRecord:
        """Reopen a suppressed or resolved situation."""
        sit = self._engine.reopen_situation(situation_id, actor, reason)
        if db:
            await self._persist_or_update_situation(sit, db)
            await db.commit()
        return sit

    async def investigate_situation(
        self,
        situation_id: str,
        scope: str | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Delegate bounded investigation tasks to swarm agents."""
        return self._engine.investigate_situation(situation_id, scope)

    async def orchestrate_situation(
        self,
        situation_id: str,
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Trigger explicit proactive deliberation and response cycle for a situation."""
        sit = await self.get_situation(situation_id, db=db)
        res = self._engine.orchestrator.deliberate_and_respond(sit)
        if asyncio.iscoroutine(res):
            res = await res
        if db:
            await self._persist_or_update_situation(sit, db)
            await db.commit()
        return res

    def get_signals_for_situation(self, situation_id: str) -> list[SignalRecord]:
        """Return all signals attached to a situation."""
        sids = self._engine._situation_signals_map.get(situation_id, [])
        return [self._engine._signals[sid] for sid in sids if sid in self._engine._signals]

    def get_timeline_for_situation(self, situation_id: str) -> list[SituationTimelineEntry]:
        """Return chronological timeline of situation."""
        sit = self._engine._situations.get(situation_id)
        if not sit:
            return []
        return sit.timeline

    def get_attention_feed(self) -> list[AttentionItem]:
        """Retrieve ranked attention feed."""
        return self._engine.get_attention_feed()

    def get_stats(self) -> dict[str, Any]:
        """Retrieve global situational awareness statistics."""
        return self._engine.get_stats()

    def get_baselines(self, environment: str | None = None) -> list[SignalBaseline]:
        """List operational baselines."""
        return self._engine.baselines.list_baselines(environment=environment)

    def get_audit_trail(self, situation_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve immutable audit events."""
        return self._engine.auditor.get_events(situation_id=situation_id, limit=limit)


situational_awareness_service = SituationalAwarenessService()
