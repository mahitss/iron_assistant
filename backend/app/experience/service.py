"""Core ExperienceService managing the lifecycle, supersession, decay, and audit of experiences."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.session import get_sessionmaker
from app.experience.models import (
    ExperienceRecord,
    LearningCandidateRecord,
    PreferenceRecord,
    UserFeedbackRecord,
)
from app.experience.safety import ExperienceSecurityGuard
from app.experience.schemas import (
    ConfidenceLevel,
    Experience,
    ExperienceScope,
    ExperienceSource,
    ExperienceStatus,
    ExperienceType,
    FailureType,
    FeedbackType,
    Preference,
    UserFeedback,
)

logger = logging.getLogger("kairo.experience.service")


class ExperienceService:
    """Manages recording, supersession, verification, and retrieval of assistant experiences."""

    def __init__(self, session_factory: Any = None) -> None:
        self.session_factory = session_factory or get_sessionmaker()
        self.settings = get_settings()

    async def record_correction(
        self,
        user_id: str,
        summary: str,
        correction: str,
        project_id: Optional[str] = None,
        scope: ExperienceScope = ExperienceScope.PROJECT,
        temporal_hours: Optional[int] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Experience:
        """Record an explicit user correction (Highest-value learning source, Section 4 & 5)."""
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=temporal_hours) if temporal_hours else None

        clean_summary = ExperienceSecurityGuard.sanitize_content(summary)
        clean_correction = ExperienceSecurityGuard.sanitize_content(correction)

        exp = Experience(
            id=str(uuid.uuid4()),
            user_id=user_id,
            project_id=project_id,
            type=ExperienceType.USER_CORRECTION,
            source=ExperienceSource.USER_EXPLICIT,
            summary=clean_summary,
            evidence={
                "correction": clean_correction,
                "recorded_at": now.isoformat(),
            },
            confidence=ConfidenceLevel.HIGH,
            status=ExperienceStatus.ACTIVE,
            scope=scope,
            created_at=now,
            updated_at=now,
            last_verified_at=now,
            expires_at=expires_at,
            metadata={"is_explicit_correction": True},
        )

        async def _persist(session: AsyncSession) -> None:
            # Check for existing conflicting experiences in the same scope to mark superseded
            stmt = select(ExperienceRecord).where(
                and_(
                    ExperienceRecord.user_id == user_id,
                    ExperienceRecord.project_id == project_id,
                    ExperienceRecord.scope == scope.value,
                    ExperienceRecord.status == ExperienceStatus.ACTIVE.value,
                    ExperienceRecord.type == ExperienceType.USER_CORRECTION.value,
                )
            )
            res = await session.execute(stmt)
            for old_rec in res.scalars().all():
                old_rec.status = ExperienceStatus.SUPERSEDED.value
                old_rec.updated_at = now

            # Insert new correction record
            db_record = ExperienceRecord(
                id=exp.id,
                user_id=exp.user_id,
                project_id=exp.project_id,
                type=exp.type.value,
                source=exp.source.value,
                summary=exp.summary,
                evidence_json=exp.evidence,
                confidence=exp.confidence.value,
                status=exp.status.value,
                scope=exp.scope.value,
                created_at=exp.created_at,
                updated_at=exp.updated_at,
                last_verified_at=exp.last_verified_at,
                expires_at=exp.expires_at,
                metadata_json=exp.metadata,
            )
            session.add(db_record)
            await session.commit()

        if db_session is not None:
            await _persist(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _persist(session)

        # Emit event to EventBus
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="experience.validated",
                    source="experience_service",
                    payload={"experience_id": exp.id, "type": exp.type.value, "summary": exp.summary},
                    user_id=user_id,
                    project_id=project_id,
                ),
                persist_log=False,
            )
        except Exception as eb_err:
            logger.debug("EventBus emission skipped: %s", eb_err)

        logger.info("Recorded user correction: %s (User: %s, Scope: %s)", exp.id, user_id, scope.value)
        return exp

    async def record_task_outcome(
        self,
        user_id: str,
        task_summary: Optional[str] = None,
        success: Optional[bool] = None,
        skill_name: Optional[str] = None,
        tools_used: Optional[List[str]] = None,
        failure_type: Optional[FailureType] = None,
        error_summary: Optional[str] = None,
        recovery_tool: Optional[str] = None,
        project_id: Optional[str] = None,
        scope: ExperienceScope = ExperienceScope.PROJECT,
        db_session: Optional[AsyncSession] = None,
        # Flexible keyword aliases
        summary: Optional[str] = None,
        outcome_success: Optional[bool] = None,
        skill: Optional[str] = None,
        tool: Optional[str] = None,
        recovery: Optional[str] = None,
    ) -> Experience:
        """Record lightweight task outcome metadata (Sections 11, 12, 13, 14)."""
        now = datetime.now(UTC)
        final_summary = summary or task_summary or "Task outcome"
        final_success = outcome_success if outcome_success is not None else (success if success is not None else True)
        final_skill = skill or skill_name
        final_recovery = recovery or recovery_tool
        all_tools = list(tools_used or [])
        if tool and tool not in all_tools:
            all_tools.append(tool)

        exp_type = ExperienceType.TASK_SUCCESS if final_success else ExperienceType.TASK_FAILURE
        clean_summary = ExperienceSecurityGuard.sanitize_content(final_summary)

        evidence: Dict[str, Any] = {
            "skill": final_skill,
            "tools_used": all_tools,
        }
        if tool:
            evidence["tool"] = tool
        if not final_success:
            evidence["failure_type"] = (failure_type.value if hasattr(failure_type, "value") else str(failure_type or "UNKNOWN")) if failure_type else FailureType.UNKNOWN.value
            evidence["error_summary"] = ExperienceSecurityGuard.sanitize_content(error_summary or "Task failed")
        if final_recovery:
            evidence["recovery"] = final_recovery
            evidence["recovery_successful"] = True

        exp = Experience(
            id=str(uuid.uuid4()),
            user_id=user_id,
            project_id=project_id,
            type=exp_type,
            source=ExperienceSource.SYSTEM_OBSERVED,
            summary=clean_summary,
            evidence=evidence,
            confidence=ConfidenceLevel.MEDIUM,
            status=ExperienceStatus.ACTIVE,
            scope=scope,
            created_at=now,
            updated_at=now,
            last_verified_at=now,
        )

        async def _persist(session: AsyncSession) -> None:
            db_record = ExperienceRecord(
                id=exp.id,
                user_id=exp.user_id,
                project_id=exp.project_id,
                type=exp.type.value,
                source=exp.source.value,
                summary=exp.summary,
                evidence_json=exp.evidence,
                confidence=exp.confidence.value,
                status=exp.status.value,
                scope=exp.scope.value,
                created_at=exp.created_at,
                updated_at=exp.updated_at,
                last_verified_at=exp.last_verified_at,
                expires_at=exp.expires_at,
                metadata_json=exp.metadata,
            )
            session.add(db_record)
            await session.commit()

        if db_session is not None:
            await _persist(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _persist(session)

        return exp

    async def record_feedback(
        self,
        user_id: str,
        feedback_type: FeedbackType,
        session_id: Optional[str] = None,
        message_id: Optional[str] = None,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        correction: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> UserFeedback:
        """Record explicit user feedback on a response (Section 33, 34)."""
        now = datetime.now(UTC)
        clean_comment = ExperienceSecurityGuard.sanitize_content(comment) if comment else None
        clean_correction = ExperienceSecurityGuard.sanitize_content(correction) if correction else None

        fb = UserFeedback(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            feedback_type=feedback_type,
            rating=rating,
            comment=clean_comment,
            correction=clean_correction,
            created_at=now,
        )

        async def _persist(session: AsyncSession) -> None:
            record = UserFeedbackRecord(
                id=fb.id,
                user_id=fb.user_id,
                session_id=fb.session_id,
                message_id=fb.message_id,
                feedback_type=fb.feedback_type.value,
                rating=fb.rating,
                comment=fb.comment,
                correction=fb.correction,
                created_at=fb.created_at,
            )
            session.add(record)
            await session.commit()

        if db_session is not None:
            await _persist(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _persist(session)

        # If correction is provided in feedback, automatically record a project-scoped correction
        if clean_correction:
            await self.record_correction(
                user_id=user_id,
                summary=clean_correction[:100],
                correction=clean_correction,
                db_session=db_session,
            )

        # Emit feedback.created event
        try:
            from app.events import event_bus
            await event_bus.publish(
                event_bus.publisher.create_event(
                    event_type="feedback.created",
                    source="experience_service",
                    payload={"feedback_id": fb.id, "type": fb.feedback_type.value, "rating": fb.rating},
                    user_id=user_id,
                ),
                persist_log=False,
            )
        except Exception as eb_err:
            logger.debug("EventBus feedback emission skipped: %s", eb_err)

        return fb

    async def set_preference(
        self,
        user_id: str,
        key: str,
        value: Any,
        scope: ExperienceScope = ExperienceScope.PROJECT,
        source: ExperienceSource = ExperienceSource.USER_EXPLICIT,
        db_session: Optional[AsyncSession] = None,
    ) -> Preference:
        """Set a durable user or project preference with safety validation (Section 7, 8)."""
        # Safety validation
        ExperienceSecurityGuard.validate_preference_safety(key, value, source)

        now = datetime.now(UTC)
        pref = Preference(
            id=str(uuid.uuid4()),
            user_id=user_id,
            scope=scope,
            key=key.strip(),
            value=value,
            source=source,
            confidence=ConfidenceLevel.HIGH if source == ExperienceSource.USER_EXPLICIT else ConfidenceLevel.MEDIUM,
            status=ExperienceStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

        async def _persist(session: AsyncSession) -> None:
            stmt = select(PreferenceRecord).where(
                and_(
                    PreferenceRecord.user_id == user_id,
                    PreferenceRecord.key == pref.key,
                    PreferenceRecord.scope == pref.scope.value,
                )
            )
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()
            if existing:
                existing.value_json = pref.value
                existing.source = pref.source.value
                existing.confidence = pref.confidence.value
                existing.status = pref.status.value
                existing.updated_at = now
                pref.id = existing.id
            else:
                record = PreferenceRecord(
                    id=pref.id,
                    user_id=pref.user_id,
                    scope=pref.scope.value,
                    key=pref.key,
                    value_json=pref.value,
                    source=pref.source.value,
                    confidence=pref.confidence.value,
                    status=pref.status.value,
                    created_at=pref.created_at,
                    updated_at=pref.updated_at,
                )
                session.add(record)
            await session.commit()

        if db_session is not None:
            await _persist(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _persist(session)

        return pref

    async def list_preferences(
        self,
        user_id: str,
        scope: Optional[ExperienceScope] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> List[Preference]:
        """List active preferences for user."""
        async def _exec(session: AsyncSession) -> List[Preference]:
            stmt = select(PreferenceRecord).where(
                and_(
                    PreferenceRecord.user_id == user_id,
                    PreferenceRecord.status == ExperienceStatus.ACTIVE.value,
                )
            )
            if scope:
                stmt = stmt.where(PreferenceRecord.scope == (scope.value if hasattr(scope, "value") else str(scope)))
            res = await session.execute(stmt)
            return [
                Preference(
                    id=r.id,
                    user_id=r.user_id,
                    scope=ExperienceScope(r.scope),
                    key=r.key,
                    value=r.value_json,
                    source=ExperienceSource(r.source),
                    confidence=ConfidenceLevel(r.confidence),
                    status=ExperienceStatus(r.status),
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                )
                for r in res.scalars().all()
            ]

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return []

    async def delete_preference(
        self,
        user_id: str,
        key: str,
        scope: ExperienceScope = ExperienceScope.PROJECT,
        db_session: Optional[AsyncSession] = None,
    ) -> bool:
        """Delete user preference."""
        async def _exec(session: AsyncSession) -> bool:
            stmt = select(PreferenceRecord).where(
                and_(
                    PreferenceRecord.user_id == user_id,
                    PreferenceRecord.key == key,
                    PreferenceRecord.scope == (scope.value if hasattr(scope, "value") else str(scope)),
                )
            )
            res = await session.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return False
            await session.delete(record)
            await session.commit()
            return True

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return False

    async def mark_stale_on_project_change(
        self,
        project_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> int:
        """Decay project experiences to STALE when project undergoes major evolution (Section 20, 21)."""
        now = datetime.now(UTC)

        async def _exec(session: AsyncSession) -> int:
            stmt = (
                update(ExperienceRecord)
                .where(
                    and_(
                        ExperienceRecord.project_id == project_id,
                        ExperienceRecord.status == ExperienceStatus.ACTIVE.value,
                    )
                )
                .values(status=ExperienceStatus.STALE.value, updated_at=now)
            )
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount or 0

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return 0

    async def delete_user_experience(
        self,
        user_id: str,
        experience_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> bool:
        """Delete an experience record enforcing strict user ownership (Section 39)."""
        now = datetime.now(UTC)

        async def _exec(session: AsyncSession) -> bool:
            stmt = select(ExperienceRecord).where(
                and_(
                    ExperienceRecord.id == experience_id,
                    ExperienceRecord.user_id == user_id,
                )
            )
            res = await session.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return False

            record.status = ExperienceStatus.DELETED.value
            record.updated_at = now
            await session.commit()
            return True

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return False

    async def get_experience(
        self,
        user_id: str,
        experience_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[Experience]:
        """Retrieve single experience by ID enforcing user isolation."""
        async def _exec(session: AsyncSession) -> Optional[Experience]:
            stmt = select(ExperienceRecord).where(
                and_(
                    ExperienceRecord.id == experience_id,
                    ExperienceRecord.user_id == user_id,
                )
            )
            res = await session.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return None
            return Experience(
                id=record.id,
                user_id=record.user_id,
                project_id=record.project_id,
                type=ExperienceType(record.type),
                source=ExperienceSource(record.source),
                summary=record.summary,
                evidence=record.evidence_json or {},
                confidence=ConfidenceLevel(record.confidence),
                status=ExperienceStatus(record.status),
                scope=ExperienceScope(record.scope),
                created_at=record.created_at,
                updated_at=record.updated_at,
                last_verified_at=record.last_verified_at,
                expires_at=record.expires_at,
                metadata=record.metadata_json or {},
            )

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return None

    async def list_experiences(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        experience_type: Optional[ExperienceType] = None,
        status: Optional[ExperienceStatus] = None,
        scope: Optional[ExperienceScope] = None,
        limit: int = 50,
        offset: int = 0,
        db_session: Optional[AsyncSession] = None,
    ) -> List[Experience]:
        """List experiences for user with optional filters, excluding DELETED by default."""
        async def _exec(session: AsyncSession) -> List[Experience]:
            query = select(ExperienceRecord).where(ExperienceRecord.user_id == user_id)
            if status:
                query = query.where(ExperienceRecord.status == (status.value if hasattr(status, "value") else str(status)))
            else:
                query = query.where(ExperienceRecord.status != ExperienceStatus.DELETED.value)

            if project_id:
                query = query.where(ExperienceRecord.project_id == project_id)
            if experience_type:
                query = query.where(ExperienceRecord.type == (experience_type.value if hasattr(experience_type, "value") else str(experience_type)))
            if scope:
                query = query.where(ExperienceRecord.scope == (scope.value if hasattr(scope, "value") else str(scope)))

            query = query.order_by(desc(ExperienceRecord.created_at)).offset(offset).limit(limit)
            res = await session.execute(query)
            return [
                Experience(
                    id=r.id,
                    user_id=r.user_id,
                    project_id=r.project_id,
                    type=ExperienceType(r.type),
                    source=ExperienceSource(r.source),
                    summary=r.summary,
                    evidence=r.evidence_json or {},
                    confidence=ConfidenceLevel(r.confidence),
                    status=ExperienceStatus(r.status),
                    scope=ExperienceScope(r.scope),
                    created_at=r.created_at,
                    updated_at=r.updated_at,
                    last_verified_at=r.last_verified_at,
                    expires_at=r.expires_at,
                    metadata=r.metadata_json or {},
                )
                for r in res.scalars().all()
            ]

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return []

    async def supersede_experience(
        self,
        user_id: str,
        experience_id: str,
        superseded_by_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Optional[Experience]:
        """Explicitly supersede an existing experience record (Section 23)."""
        now = datetime.now(UTC)

        async def _exec(session: AsyncSession) -> Optional[Experience]:
            stmt = select(ExperienceRecord).where(
                and_(
                    ExperienceRecord.id == experience_id,
                    ExperienceRecord.user_id == user_id,
                )
            )
            res = await session.execute(stmt)
            record = res.scalar_one_or_none()
            if not record:
                return None

            record.status = ExperienceStatus.SUPERSEDED.value
            record.updated_at = now
            if not record.metadata_json:
                record.metadata_json = {}
            record.metadata_json["superseded_by"] = superseded_by_id
            await session.commit()
            await session.refresh(record)

            return Experience(
                id=record.id,
                user_id=record.user_id,
                project_id=record.project_id,
                type=ExperienceType(record.type),
                source=ExperienceSource(record.source),
                summary=record.summary,
                evidence=record.evidence_json or {},
                confidence=ConfidenceLevel(record.confidence),
                status=ExperienceStatus(record.status),
                scope=ExperienceScope(record.scope),
                created_at=record.created_at,
                updated_at=record.updated_at,
                last_verified_at=record.last_verified_at,
                expires_at=record.expires_at,
                metadata=record.metadata_json or {},
            )

        if db_session is not None:
            return await _exec(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                return await _exec(session)
        return None

    async def export_user_data(
        self,
        user_id: str,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Safe structured export of user memory, preferences, experiences (Section 40)."""
        experiences: List[Dict[str, Any]] = []
        preferences: List[Dict[str, Any]] = []
        feedback_items: List[Dict[str, Any]] = []

        async def _collect(session: AsyncSession) -> None:
            # Experiences
            exp_stmt = select(ExperienceRecord).where(
                and_(
                    ExperienceRecord.user_id == user_id,
                    ExperienceRecord.status != ExperienceStatus.DELETED.value,
                )
            ).order_by(desc(ExperienceRecord.created_at))
            res = await session.execute(exp_stmt)
            for r in res.scalars().all():
                experiences.append({
                    "id": r.id,
                    "type": r.type,
                    "scope": r.scope,
                    "summary": r.summary,
                    "confidence": r.confidence,
                    "created_at": r.created_at.isoformat(),
                })

            # Preferences
            pref_stmt = select(PreferenceRecord).where(
                PreferenceRecord.user_id == user_id
            )
            res_pref = await session.execute(pref_stmt)
            for p in res_pref.scalars().all():
                preferences.append({
                    "key": p.key,
                    "value": p.value_json,
                    "scope": p.scope,
                    "confidence": p.confidence,
                })

            # Feedback
            fb_stmt = select(UserFeedbackRecord).where(
                UserFeedbackRecord.user_id == user_id
            )
            res_fb = await session.execute(fb_stmt)
            for f in res_fb.scalars().all():
                feedback_items.append({
                    "type": f.feedback_type,
                    "rating": f.rating,
                    "comment": f.comment,
                    "correction": f.correction,
                    "created_at": f.created_at.isoformat(),
                })

        if db_session is not None:
            await _collect(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _collect(session)

        return {
            "user_id": user_id,
            "exported_at": datetime.now(UTC).isoformat(),
            "preferences": preferences,
            "experiences": experiences,
            "feedback": feedback_items,
        }


experience_service = ExperienceService()
