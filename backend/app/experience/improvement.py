"""Improvement Pipeline and Learning Candidate Management for Kairo.

Implements the controlled improvement loop:
Experience
  ↓
Learning Candidate
  ↓
Evaluation Dataset (Scenario / Benchmark)
  ↓
Human / Engineering Review
  ↓
Controlled Release

Strictly enforces:
- No autonomous policy changes (SecurityCenter, Permissions, Tool allowlists, Risk tiers)
- No autonomous code or prompt modifications
- Sanitization of private content and credentials
- Explainable, bounded, and traceable learning
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_sessionmaker
from app.experience.models import (
    ExperienceRecord,
    LearningCandidateRecord,
    UserFeedbackRecord,
)
from app.experience.safety import (
    ExperienceSecurityGuard,
    ExperienceSecurityViolation,
    sanitize_content,
    validate_learning_candidate,
)
from app.experience.schemas import (
    CandidateStatus,
    ConfidenceLevel,
    ExperienceScope,
    ExperienceStatus,
    ExperienceType,
    FailureType,
    LearningCandidate,
)

logger = logging.getLogger("kairo.experience.improvement")


class ImprovementPipeline:
    """Orchestrates controlled candidate learning, failure/success analysis,

    and evaluation dataset integration without autonomous mutation of production code or policies.
    """

    def __init__(self, session_factory: Any = None) -> None:
        self.session_factory = session_factory or get_sessionmaker()

    async def propose_candidate(
        self,
        source_event: str,
        proposed_change: str,
        evidence: Dict[str, Any],
        scope: ExperienceScope = ExperienceScope.GLOBAL,
        confidence: ConfidenceLevel = ConfidenceLevel.LOW,
        experience_id: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> LearningCandidate:
        """Create a new proposed learning candidate subject to safety validation."""
        # Validate that proposed change does not target protected security or policy governance
        validate_learning_candidate(proposed_change, scope.value)

        # Sanitize evidence to strip potential secrets or private details
        sanitized_evidence = sanitize_content(evidence)

        now = datetime.now(UTC)
        cand_id = f"cand-{uuid.uuid4().hex[:12]}"

        candidate_obj = LearningCandidate(
            id=cand_id,
            experience_id=experience_id,
            source_event=source_event,
            proposed_change=proposed_change,
            evidence=sanitized_evidence,
            confidence=confidence,
            scope=scope,
            status=CandidateStatus.PROPOSED,
            created_at=now,
            updated_at=now,
        )

        async def _persist(session: AsyncSession) -> None:
            record = LearningCandidateRecord(
                id=candidate_obj.id,
                experience_id=candidate_obj.experience_id,
                source_event=candidate_obj.source_event,
                proposed_change=candidate_obj.proposed_change,
                evidence=candidate_obj.evidence,
                confidence=candidate_obj.confidence.value,
                scope=candidate_obj.scope.value,
                status=candidate_obj.status.value,
                created_at=candidate_obj.created_at,
                updated_at=candidate_obj.updated_at,
            )
            session.add(record)
            await session.commit()

        if db_session is not None:
            await _persist(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _persist(session)

        logger.info(
            "Proposed learning candidate %s: '%s' (scope=%s, confidence=%s)",
            cand_id,
            proposed_change[:60],
            scope.value,
            confidence.value,
        )
        return candidate_obj

    async def create_candidate_from_task_failure(
        self,
        experience: ExperienceRecord,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[LearningCandidate]:
        """Convert a task or workflow failure into an evaluation learning candidate."""
        if experience.type not in (ExperienceType.TASK_FAILURE.value, ExperienceType.WORKFLOW_OUTCOME.value):
            return None

        evidence = experience.evidence or {}
        failure_type = evidence.get("failure_type", FailureType.UNKNOWN.value)
        error_msg = evidence.get("error_message", "Unknown error")
        skill_name = evidence.get("skill")
        tool_name = evidence.get("tool")

        target_entity = skill_name or tool_name or "workflow"
        proposed = f"Add evaluation regression benchmark for {target_entity} handling: {error_msg[:80]}"

        return await self.propose_candidate(
            source_event=f"task_failure:{failure_type}",
            proposed_change=proposed,
            evidence={
                "failure_type": failure_type,
                "skill": skill_name,
                "tool": tool_name,
                "project_id": experience.project_id,
                "summary": experience.summary,
                "recovery": evidence.get("recovery"),
            },
            scope=ExperienceScope(experience.scope) if experience.scope else ExperienceScope.GLOBAL,
            confidence=ConfidenceLevel.LOW,
            experience_id=experience.id,
            db_session=db_session,
        )

    async def review_candidate(
        self,
        candidate_id: str,
        decision: CandidateStatus,
        reviewer_id: str,
        review_notes: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[LearningCandidate]:
        """Human/Engineering review of a learning candidate."""
        if decision not in (CandidateStatus.ACCEPTED, CandidateStatus.REJECTED, CandidateStatus.EXPIRED):
            raise ValueError(f"Invalid review decision: {decision}")

        now = datetime.now(UTC)

        async def _exec(session: AsyncSession) -> Optional[LearningCandidate]:
            stmt = select(LearningCandidateRecord).where(LearningCandidateRecord.id == candidate_id)
            res = await session.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return None

            record.status = decision.value
            record.reviewer_id = reviewer_id
            record.review_notes = review_notes
            record.updated_at = now
            await session.commit()
            await session.refresh(record)

            return LearningCandidate(
                id=record.id,
                experience_id=record.experience_id,
                source_event=record.source_event,
                proposed_change=record.proposed_change,
                evidence=record.evidence or {},
                confidence=ConfidenceLevel(record.confidence),
                scope=ExperienceScope(record.scope),
                status=CandidateStatus(record.status),
                reviewer_id=record.reviewer_id,
                review_notes=record.review_notes,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return None

    async def list_candidates(
        self,
        status: Optional[CandidateStatus] = None,
        limit: int = 50,
        db_session: Optional[AsyncSession] = None,
    ) -> List[LearningCandidate]:
        """List learning candidates for review."""
        async def _exec(session: AsyncSession) -> List[LearningCandidate]:
            query = select(LearningCandidateRecord).order_by(desc(LearningCandidateRecord.created_at))
            if status:
                query = query.where(LearningCandidateRecord.status == status.value)
            query = query.limit(limit)

            res = await session.execute(query)
            records = res.scalars().all()
            return [
                LearningCandidate(
                    id=r.id,
                    experience_id=r.experience_id,
                    source_event=r.source_event,
                    proposed_change=r.proposed_change,
                    evidence=r.evidence or {},
                    confidence=ConfidenceLevel(r.confidence),
                    scope=ExperienceScope(r.scope),
                    status=CandidateStatus(r.status),
                    reviewer_id=r.reviewer_id,
                    review_notes=r.review_notes,
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in records
            ]

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return []

    async def generate_evaluation_scenario(
        self,
        candidate_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Generate a structured evaluation scenario definition from a candidate."""
        async def _exec(session: AsyncSession) -> Dict[str, Any]:
            stmt = select(LearningCandidateRecord).where(LearningCandidateRecord.id == candidate_id)
            res = await session.execute(stmt)
            candidate = res.scalar_one_or_none()
            if not candidate:
                raise ValueError(f"Candidate {candidate_id} not found")

            evidence = candidate.evidence or {}
            scenario_id = f"eval-scen-{candidate.id}"

            return {
                "scenario_id": scenario_id,
                "candidate_id": candidate.id,
                "source_event": candidate.source_event,
                "name": f"Regression_{candidate.source_event}_{candidate.id}",
                "description": candidate.proposed_change,
                "scope": candidate.scope,
                "target_skill": evidence.get("skill"),
                "target_tool": evidence.get("tool"),
                "expected_outcome": "SUCCESS",
                "failure_pattern_to_avoid": evidence.get("failure_type"),
                "created_at": datetime.now(UTC).isoformat(),
                "synthetic_inputs": {
                    "task_description": f"Test case generated from failure in {candidate.source_event}",
                    "parameters": {"simulated_error_recovery": bool(evidence.get("recovery"))},
                },
            }

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        raise ValueError("Database unavailable")

    async def analyze_failures(
        self,
        days: int = 30,
        skill: Optional[str] = None,
        tool: Optional[str] = None,
        project_id: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Aggregate failure patterns safely without exposing raw user payloads."""
        async def _exec(session: AsyncSession) -> Dict[str, Any]:
            query = select(ExperienceRecord).where(
                ExperienceRecord.type == ExperienceType.TASK_FAILURE.value
            )
            if project_id:
                query = query.where(ExperienceRecord.project_id == project_id)

            res = await session.execute(query)
            records = res.scalars().all()

            by_failure_type: Dict[str, int] = {}
            by_skill: Dict[str, int] = {}
            by_tool: Dict[str, int] = {}
            total = len(records)

            for rec in records:
                ev = rec.evidence or {}
                ft = ev.get("failure_type", FailureType.UNKNOWN.value)
                sk = ev.get("skill")
                tl = ev.get("tool")

                if skill and sk != skill:
                    continue
                if tool and tl != tool:
                    continue

                by_failure_type[ft] = by_failure_type.get(ft, 0) + 1
                if sk:
                    by_skill[sk] = by_skill.get(sk, 0) + 1
                if tl:
                    by_tool[tl] = by_tool.get(tl, 0) + 1

            return {
                "total_failures": total,
                "by_failure_type": by_failure_type,
                "by_skill": by_skill,
                "by_tool": by_tool,
                "window_days": days,
            }

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return {"total_failures": 0, "by_failure_type": {}, "by_skill": {}, "by_tool": {}, "window_days": days}
