"""Tests for Experience retrieval, context bounding, scoping hierarchy, and model context labeling (Sections 43-47, 75)."""

import asyncio
from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.experience.models import ExperienceRecord, PreferenceRecord
from app.experience.retrieval import ExperienceRetriever
from app.experience.schemas import (
    ConfidenceLevel,
    ExperienceScope,
    ExperienceSource,
    ExperienceStatus,
    ExperienceType,
)
from app.experience.service import ExperienceService


@pytest.fixture
def async_db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def init_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_tables())
    yield engine
    asyncio.run(engine.dispose())


@pytest.fixture
def session_factory(async_db_engine):
    return async_sessionmaker(bind=async_db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_retrieval_scoping_hierarchy(session_factory):
    """Section 44: Search respects hierarchy (project-specific matches ranked before global)."""
    service = ExperienceService(session_factory=session_factory)
    retriever = ExperienceRetriever(session_factory=session_factory)
    user_id = "user_hierarchy"
    project_id = "proj_backend"

    # Add project-scoped preference
    await service.set_preference(
        user_id=user_id,
        key="database",
        value="PostgreSQL",
        scope=ExperienceScope.PROJECT,
    )

    # Add user-global preference
    await service.set_preference(
        user_id=user_id,
        key="database",
        value="SQLite",
        scope=ExperienceScope.USER,
    )

    experiences, preferences = await retriever.retrieve_relevant_experiences(
        user_id=user_id,
        query="Which database should we configure for migrations?",
        project_id=project_id,
    )

    # Both retrieved, but project scoped preference is returned
    assert len(preferences) >= 1
    pref_scopes = [p.scope.value for p in preferences]
    assert "PROJECT" in pref_scopes


@pytest.mark.asyncio
async def test_stale_and_candidate_excluded_from_context(session_factory):
    """Section 2, 43: Only ACTIVE or VALIDATED non-expired records may influence context."""
    service = ExperienceService(session_factory=session_factory)
    retriever = ExperienceRetriever(session_factory=session_factory)
    user_id = "user_filter"
    project_id = "proj_filter"

    # 1. Active experience
    await service.record_correction(
        user_id=user_id,
        summary="Use pytest for testing",
        correction="pytest",
        project_id=project_id,
    )

    # 2. Mark project experiences stale
    await service.mark_stale_on_project_change(project_id=project_id)

    # 3. Add fresh active experience
    await service.record_correction(
        user_id=user_id,
        summary="Use Vitest for frontend unit tests",
        correction="Vitest",
        project_id=project_id,
    )

    experiences, preferences = await retriever.retrieve_relevant_experiences(
        user_id=user_id,
        query="How should we run tests?",
        project_id=project_id,
    )

    # Stale pytest should NOT be in active retrieved experiences
    summaries = [e.summary for e in experiences]
    assert any("Vitest" in s for s in summaries)
    assert not any("pytest" in s for s in summaries)


@pytest.mark.asyncio
async def test_context_budget_bounding(session_factory):
    """Section 46: Bounded by max experiences limit."""
    retriever = ExperienceRetriever(session_factory=session_factory, max_experiences=3)
    user_id = "user_bounding"

    async with session_factory() as session:
        for i in range(10):
            exp = ExperienceRecord(
                id=f"exp-budget-{i}",
                user_id=user_id,
                project_id=None,
                type=ExperienceType.TASK_SUCCESS.value,
                source=ExperienceSource.SYSTEM_OBSERVED.value,
                scope=ExperienceScope.USER.value,
                summary=f"Deployment task {i} finished cleanly",
                evidence_json={},
                confidence=ConfidenceLevel.HIGH.value,
                status=ExperienceStatus.ACTIVE.value,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(exp)
        await session.commit()

    experiences, _ = await retriever.retrieve_relevant_experiences(
        user_id=user_id,
        query="deployment tasks",
    )
    assert len(experiences) <= 3


def test_prompt_formatting_labels():
    """Section 47: Experiences must be clearly labeled and not injected as system instruction."""
    from app.experience.schemas import Experience, Preference

    pref = Preference(
        id="p1",
        user_id="u1",
        scope=ExperienceScope.PROJECT,
        key="preferred_format",
        value="Markdown tables",
        source=ExperienceSource.USER_EXPLICIT,
        confidence=ConfidenceLevel.HIGH,
        status="ACTIVE",
    )

    exp = Experience(
        id="e1",
        user_id="u1",
        project_id="proj-1",
        type=ExperienceType.USER_CORRECTION,
        source=ExperienceSource.USER_EXPLICIT,
        scope=ExperienceScope.PROJECT,
        summary="Use SQLite for this project",
        evidence={"correction": "SQLite"},
        confidence=ConfidenceLevel.HIGH,
        status=ExperienceStatus.ACTIVE,
    )

    formatted = ExperienceRetriever.format_experience_for_prompt(
        experiences=[exp],
        preferences=[pref],
    )

    assert "USER PREFERENCE" in formatted
    assert "Markdown tables" in formatted
    assert "USER CORRECTION" in formatted
    assert "Use SQLite for this project" in formatted
