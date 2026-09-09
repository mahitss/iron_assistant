"""Scoped experience and preference retrieval for Context Engine injection.

Enforces narrow-first scoping (task -> project -> user), context budgeting,
and labeled prompt formatting.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.db.session import get_sessionmaker
from app.experience.models import ExperienceRecord, PreferenceRecord
from app.experience.schemas import (
    ConfidenceLevel,
    Experience,
    ExperienceScope,
    ExperienceSource,
    ExperienceStatus,
    ExperienceType,
    Preference,
)

logger = logging.getLogger("kairo.experience.retrieval")


class ExperienceRetriever:
    """Retrieves and ranks relevant experiences and preferences for personal assistant turns."""

    def __init__(
        self,
        session_factory: Any = None,
        max_experiences: Optional[int] = None,
        max_preferences: Optional[int] = None,
    ) -> None:
        self.session_factory = session_factory or get_sessionmaker()
        self.settings = get_settings()
        self.max_experiences = max_experiences
        self.max_preferences = max_preferences

    async def retrieve_relevant_experiences(
        self,
        user_id: str,
        query: str,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: Optional[int] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> tuple[List[Experience], List[Preference]]:
        """Retrieve scoped experiences and preferences ranked by specificity (task -> project -> user)."""
        if not getattr(self.settings, "KAIRO_EXPERIENCE_ENABLED", True):
            return ([], [])

        max_limit = limit or self.max_experiences or getattr(self.settings, "KAIRO_MAX_EXPERIENCE_CONTEXT", 10)
        now = datetime.now(UTC)
        results: List[Experience] = []

        async def _query(session: AsyncSession) -> None:
            conditions = [
                ExperienceRecord.user_id == user_id,
                ExperienceRecord.status.in_([ExperienceStatus.ACTIVE.value, ExperienceStatus.VALIDATED.value]),
                or_(ExperienceRecord.expires_at.is_(None), ExperienceRecord.expires_at > now),
            ]

            if project_id:
                conditions.append(
                    or_(
                        ExperienceRecord.project_id == project_id,
                        ExperienceRecord.scope.in_([ExperienceScope.USER.value, ExperienceScope.GLOBAL.value]),
                    )
                )

            stmt = (
                select(ExperienceRecord)
                .where(and_(*conditions))
                .order_by(
                    desc(ExperienceRecord.confidence),
                    desc(ExperienceRecord.created_at),
                )
                .limit(max_limit)
            )

            res = await session.execute(stmt)
            for r in res.scalars().all():
                results.append(
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
                )

        if db_session is not None:
            await _query(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _query(session)

        # Scoped sorting: project-specific corrections rank higher than global task outcomes
        results.sort(
            key=lambda e: (
                1 if e.project_id == project_id and project_id else 0,
                1 if e.confidence.value == "HIGH" else 0,
                e.created_at,
            ),
            reverse=True,
        )

        # Retrieve relevant preferences as well
        prefs = await self.retrieve_preferences(
            user_id=user_id,
            project_id=project_id,
            limit=self.max_preferences,
            db_session=db_session,
        )

        return (results[:max_limit], prefs)

    async def retrieve_preferences(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        limit: Optional[int] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> List[Preference]:
        """Retrieve active user and project preferences."""
        max_limit = limit or getattr(self.settings, "KAIRO_MAX_PREFERENCE_CONTEXT", 10)
        results: List[Preference] = []

        async def _query(session: AsyncSession) -> None:
            stmt = (
                select(PreferenceRecord)
                .where(
                    and_(
                        PreferenceRecord.user_id == user_id,
                        PreferenceRecord.status == ExperienceStatus.ACTIVE.value,
                    )
                )
                .order_by(desc(PreferenceRecord.updated_at))
                .limit(max_limit)
            )
            res = await session.execute(stmt)
            for p in res.scalars().all():
                results.append(
                    Preference(
                        id=p.id,
                        user_id=p.user_id,
                        scope=ExperienceScope(p.scope),
                        key=p.key,
                        value=p.value_json,
                        source=ExperienceSource(p.source),
                        confidence=ConfidenceLevel(p.confidence),
                        status=ExperienceStatus(p.status),
                        created_at=p.created_at,
                        updated_at=p.updated_at,
                    )
                )

        if db_session is not None:
            await _query(db_session)
        elif self.session_factory is not None:
            async with self.session_factory() as session:
                await _query(session)

        return results[:max_limit]

    @staticmethod
    def format_experience_for_prompt(
        experiences: List[Experience],
        preferences: Optional[List[Preference]] = None,
    ) -> str:
        """Format experiences and preferences with clear provenance and scope labeling (Section 47)."""
        if not experiences and not preferences:
            return ""

        lines: List[str] = ["=== ASSISTANT EXPERIENCE & USER PREFERENCES ==="]

        if preferences:
            lines.append("USER PREFERENCES:")
            for p in preferences:
                scope_str = p.scope.value if hasattr(p.scope, "value") else str(p.scope)
                lines.append(f"- [{scope_str}] {p.key}: {p.value}")

        if experiences:
            lines.append("RELEVANT EXPERIENCE:")
            for e in experiences:
                type_label = e.type.value if hasattr(e.type, "value") else str(e.type)
                scope_label = e.scope.value if hasattr(e.scope, "value") else str(e.scope)
                lines.append(f"- [{type_label.replace('_', ' ')} | {scope_label}] {e.summary}")

        lines.append("================================================")
        return "\n".join(lines)


experience_retriever = ExperienceRetriever()
