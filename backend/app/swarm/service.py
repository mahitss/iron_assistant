"""Transactional service layer for Collective Intelligence & Swarm Reasoning Engine (Task 64)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.swarm.audit import AuditRecord
from app.swarm.engine import SwarmReasoningEngine, swarm_engine
from app.swarm.models import (
    SwarmDisagreementModel,
    SwarmMinorityReportModel,
    SwarmResultModel,
    SwarmSessionModel,
    SwarmTaskModel,
)
from app.swarm.schemas import (
    AgentResult,
    CollectiveObjective,
    CollectiveResult,
    DisagreementRecord,
    MinorityReport,
    PeerReview,
    SwarmAgentSpec,
    SwarmCreateRequest,
    SwarmSession,
    SwarmTaskNode,
)

logger = logging.getLogger(__name__)


class SwarmService:
    """Service facade coordinating SwarmReasoningEngine with persistence and audit logging."""

    def __init__(self, engine: SwarmReasoningEngine | None = None) -> None:
        self._engine = engine or swarm_engine

    async def create_and_execute_session(
        self,
        req: SwarmCreateRequest,
        db: AsyncSession | None = None,
    ) -> SwarmSession:
        """Create and autonomously execute a collective reasoning session."""
        objective = CollectiveObjective(
            goal=req.goal,
            context=req.context,
            constraints=req.constraints,
            priority=req.priority,
            risk_level=req.risk_level,
            tenant_id=req.tenant_id,
        )

        session = self._engine.execute_swarm_session(
            objective=objective,
            topology=req.topology,
            requested_roles=req.roles,
        )

        # Optional DB persistence
        if db:
            try:
                db_session = SwarmSessionModel(
                    swarm_id=session.swarm_id,
                    goal=session.objective.goal,
                    topology=session.topology.value,
                    status=session.status.value,
                    tenant_id=session.tenant_id,
                    consensus_score=session.consensus.consensus_score if session.consensus else 0.0,
                    confidence=session.final_result.confidence if session.final_result else 0.0,
                    verification_status=session.final_result.verification_status
                    if session.final_result
                    else "UNVERIFIED",
                    summary=session.final_result.summary if session.final_result else "",
                )
                db.add(db_session)

                # Persist tasks
                if session.task_dag:
                    for t in session.task_dag.tasks:
                        db_t = SwarmTaskModel(
                            task_id=t.task_id,
                            swarm_id=session.swarm_id,
                            title=t.title,
                            role_needed=t.role_needed,
                            assigned_agent_id=t.assigned_agent_id,
                            status=t.status.value,
                            is_critical_path=t.is_critical_path,
                            result_id=t.result_id,
                            error=t.error,
                        )
                        db.add(db_t)

                # Persist results
                for r in session.results:
                    db_r = SwarmResultModel(
                        result_id=r.result_id,
                        swarm_id=session.swarm_id,
                        agent_id=r.agent_id,
                        task_id=r.task_id,
                        role=r.role,
                        answer=r.answer[:2000],
                        confidence=r.confidence,
                    )
                    db.add(db_r)

                # Persist disagreements
                for d in session.disagreements:
                    db_d = SwarmDisagreementModel(
                        disagreement_id=d.disagreement_id,
                        swarm_id=session.swarm_id,
                        category=d.category.value,
                        issue=d.issue[:500],
                        severity=d.severity,
                        status=d.status,
                        resolution=d.resolution[:500] if d.resolution else None,
                    )
                    db.add(db_d)

                # Persist minority reports
                for m in session.minority_reports:
                    db_m = SwarmMinorityReportModel(
                        minority_id=m.minority_id,
                        swarm_id=session.swarm_id,
                        dissenting_agent_id=m.dissenting_agent_id,
                        dissenting_role=m.dissenting_role,
                        position=m.position[:1000],
                        reasoning=m.reasoning[:1000],
                        confidence=m.confidence,
                    )
                    db.add(db_m)

                await db.commit()
            except Exception as db_err:
                logger.warning("SWARM_DB_PERSISTENCE_FAILED: %s", str(db_err))
                await db.rollback()

        return session

    def get_session(self, swarm_id: str) -> SwarmSession | None:
        return self._engine.get_session(swarm_id)

    def list_sessions(self, limit: int = 20) -> list[SwarmSession]:
        return list(self._engine._active_sessions.values())[-limit:]

    def pause_session(self, swarm_id: str) -> SwarmSession:
        return self._engine.pause_session(swarm_id)

    def resume_session(self, swarm_id: str) -> SwarmSession:
        return self._engine.resume_session(swarm_id)

    def cancel_session(self, swarm_id: str, reason: str = "") -> SwarmSession:
        return self._engine.cancel_session(swarm_id, reason=reason)

    def verify_session(self, swarm_id: str, notes: str | None = None) -> CollectiveResult:
        return self._engine.verify_session_result(swarm_id, verifier_notes=notes)

    def replay_session(self, swarm_id: str) -> dict[str, Any]:
        return self._engine.replay_session(swarm_id)

    def list_agents(self, swarm_id: str) -> list[SwarmAgentSpec]:
        sess = self.get_session(swarm_id)
        if not sess:
            return []
        return sess.agents

    def list_tasks(self, swarm_id: str) -> list[SwarmTaskNode]:
        sess = self.get_session(swarm_id)
        if not sess or not sess.task_dag:
            return []
        return sess.task_dag.tasks

    def list_results(self, swarm_id: str) -> list[AgentResult]:
        sess = self.get_session(swarm_id)
        if not sess:
            return []
        return sess.results

    def list_reviews(self, swarm_id: str) -> list[PeerReview]:
        sess = self.get_session(swarm_id)
        if not sess:
            return []
        return sess.reviews

    def list_disagreements(self, swarm_id: str) -> list[DisagreementRecord]:
        sess = self.get_session(swarm_id)
        if not sess:
            return []
        return sess.disagreements

    def list_minority_reports(self, swarm_id: str) -> list[MinorityReport]:
        sess = self.get_session(swarm_id)
        if not sess:
            return []
        return sess.minority_reports

    def get_audit_trail(self, swarm_id: str | None = None, limit: int = 100) -> list[AuditRecord]:
        return self._engine.auditor.get_audit_trail(session_id=swarm_id, limit=limit)


swarm_service = SwarmService()
