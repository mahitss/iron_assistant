"""Unit and integration tests for ExperienceService operations (Sections 4, 5, 11-14, 20-23, 33-40, 54, 55)."""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.experience.models import ExperienceRecord, PreferenceRecord, UserFeedbackRecord
from app.experience.schemas import (
    ConfidenceLevel,
    ExperienceScope,
    ExperienceSource,
    ExperienceStatus,
    ExperienceType,
    FailureType,
    FeedbackType,
)
from app.experience.service import ExperienceService


@pytest.fixture
def async_db_engine():
    """Setup isolated in-memory SQLite engine for async testing."""
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
async def test_record_correction_and_supersession(session_factory):
    """Sections 4, 5, 23, 54: Explicit user correction supersedes older conflicting active records."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_1"
    project_id = "project_x"

    # Step 1: Initial correction
    exp1 = await service.record_correction(
        user_id=user_id,
        summary="Use PostgreSQL for this project",
        correction="We are using PostgreSQL",
        project_id=project_id,
        scope=ExperienceScope.PROJECT,
    )
    assert exp1.status == ExperienceStatus.ACTIVE
    assert exp1.confidence == ConfidenceLevel.HIGH
    assert exp1.source == ExperienceSource.USER_EXPLICIT

    # Step 2: New contradictory correction for the same project
    exp2 = await service.record_correction(
        user_id=user_id,
        summary="No, we migrated to SQLite for this project",
        correction="Actually, use SQLite",
        project_id=project_id,
        scope=ExperienceScope.PROJECT,
    )
    assert exp2.status == ExperienceStatus.ACTIVE

    # Step 3: Verify exp1 was marked SUPERSEDED
    old_exp1 = await service.get_experience(user_id=user_id, experience_id=exp1.id)
    assert old_exp1 is not None
    assert old_exp1.status == ExperienceStatus.SUPERSEDED


@pytest.mark.asyncio
async def test_record_task_failure_with_recovery(session_factory):
    """Sections 11, 12, 13, 14: Record task failure with classified FailureType and recovery tool."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_2"

    exp = await service.record_task_outcome(
        user_id=user_id,
        summary="Github CI run inspection recovered via tool B",
        outcome_success=False,
        failure_type=FailureType.TOOL_FAILURE,
        skill="developer_workflow",
        tool="github.get_runs",
        recovery="Recovered by querying github.list_workflow_runs instead.",
    )
    assert exp.type == ExperienceType.TASK_FAILURE
    assert exp.evidence["failure_type"] == FailureType.TOOL_FAILURE.value
    assert exp.evidence["tool"] == "github.get_runs"
    assert "github.list_workflow_runs" in exp.evidence["recovery"]


@pytest.mark.asyncio
async def test_feedback_with_correction_triggers_correction(session_factory):
    """Sections 33, 35, 62: Feedback with correction auto-records project correction."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_3"

    fb = await service.record_feedback(
        user_id=user_id,
        feedback_type=FeedbackType.CORRECTION,
        rating=2,
        comment="Wrong database mentioned in summary",
        correction="The project uses Redis for caching, not Memcached",
    )
    assert fb.feedback_type == FeedbackType.CORRECTION

    # Verify a correction experience was automatically created
    experiences = await service.list_experiences(
        user_id=user_id,
        experience_type=ExperienceType.USER_CORRECTION,
    )
    assert len(experiences) >= 1
    assert "Redis" in experiences[0].summary or "Redis" in experiences[0].evidence.get("correction", "")


@pytest.mark.asyncio
async def test_preferences_lifecycle(session_factory):
    """Sections 7, 8: Preference set, list, delete with scope."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_4"

    pref = await service.set_preference(
        user_id=user_id,
        key="preferred_format",
        value="bullet_points",
        scope=ExperienceScope.USER,
    )
    assert pref.key == "preferred_format"
    assert pref.value == "bullet_points"

    prefs = await service.list_preferences(user_id=user_id)
    assert len(prefs) == 1
    assert prefs[0].key == "preferred_format"

    deleted = await service.delete_preference(user_id=user_id, key="preferred_format", scope=ExperienceScope.USER)
    assert deleted is True

    prefs_after = await service.list_preferences(user_id=user_id)
    assert len(prefs_after) == 0


@pytest.mark.asyncio
async def test_project_evolution_decay_to_stale(session_factory):
    """Sections 20, 21: Mark project experiences STALE on project change."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_5"
    project_id = "proj_decay"

    exp = await service.record_task_outcome(
        user_id=user_id,
        summary="Initial deployment to Kubernetes cluster",
        outcome_success=True,
        project_id=project_id,
    )
    assert exp.status == ExperienceStatus.ACTIVE

    stale_count = await service.mark_stale_on_project_change(project_id=project_id)
    assert stale_count == 1

    updated_exp = await service.get_experience(user_id=user_id, experience_id=exp.id)
    assert updated_exp.status == ExperienceStatus.STALE


@pytest.mark.asyncio
async def test_user_experience_deletion(session_factory):
    """Section 39: Deletion removes accessibility for user."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_6"

    exp = await service.record_correction(
        user_id=user_id,
        summary="Use Node.js for backend",
        correction="Node.js",
    )
    deleted = await service.delete_user_experience(user_id=user_id, experience_id=exp.id)
    assert deleted is True

    # Deleted item should not be retrieved in normal listings
    active_list = await service.list_experiences(user_id=user_id)
    assert len(active_list) == 0


@pytest.mark.asyncio
async def test_temporal_preference_expires(session_factory):
    """Section 55: Temporal preference sets expires_at."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_7"

    exp = await service.record_correction(
        user_id=user_id,
        summary="Today use concise bullet answers",
        correction="Concise bullets",
        temporal_hours=12,
    )
    assert exp.expires_at is not None
    assert exp.scope == ExperienceScope.PROJECT


@pytest.mark.asyncio
async def test_data_export(session_factory):
    """Section 40: Structured export without leaking security internals."""
    service = ExperienceService(session_factory=session_factory)
    user_id = "test_user_8"

    await service.set_preference(user_id=user_id, key="theme", value="dark")
    await service.record_correction(user_id=user_id, summary="Use tabs not spaces", correction="Tabs")

    export = await service.export_user_data(user_id=user_id)
    assert export["user_id"] == user_id
    assert len(export["preferences"]) == 1
    assert len(export["experiences"]) == 1
    assert "security_tokens" not in export
    assert "approval_secrets" not in export
