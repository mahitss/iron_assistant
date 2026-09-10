"""Test suite for Experience Replay, Simulation Isolation, Temporal Anti-Leakage, and Safe Consolidation (Task 52)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.learning.consolidation import ContradictoryConsolidationError, ExperienceConsolidator
from app.learning.experiences import Experience
from app.learning.lessons import LessonExtractor
from app.learning.replay import ExperienceReplayEngine, TemporalLeakageError
from app.learning.schemas import GeneralizationScope, LessonStatus, LessonType


def test_experience_replay_simulation_isolation_and_success():
    """INVARIANT 30-32: Replay runs in simulation mode without side effects."""
    engine = ExperienceReplayEngine()
    past_time = datetime.now(UTC) - timedelta(days=2)
    exp = Experience(
        task_id="task-hist-1",
        actions=[{"action": "format_disk_simulated"}],
        outcome="SUCCESS",
        timestamp=past_time,
    )

    cutoff = datetime.now(UTC) - timedelta(days=1)
    replay = engine.replay_experience(
        experience=exp,
        simulation_context={"mock_fs": True},
        temporal_cutoff=cutoff,
    )

    assert replay.experience_id == exp.experience_id
    assert replay.evaluation_result["simulated"] is True
    assert replay.evaluation_result["side_effects_executed"] is False
    assert replay.leakage_detected is False


def test_experience_replay_detects_temporal_leakage_from_future_experience():
    """INVARIANT 33-35: Replay raises TemporalLeakageError if experience timestamp is after cutoff."""
    engine = ExperienceReplayEngine()
    future_time = datetime.now(UTC)
    cutoff = datetime.now(UTC) - timedelta(hours=1)

    exp = Experience(
        task_id="task-future-1",
        actions=[{"action": "deploy"}],
        outcome="SUCCESS",
        timestamp=future_time,
    )

    with pytest.raises(TemporalLeakageError, match="INVARIANT 34"):
        engine.replay_experience(
            experience=exp,
            simulation_context={},
            temporal_cutoff=cutoff,
        )


def test_experience_replay_detects_temporal_leakage_from_simulation_features():
    """INVARIANT 35: Replay detects future information leaked into simulation context."""
    engine = ExperienceReplayEngine()
    past_time = datetime.now(UTC) - timedelta(days=5)
    cutoff = datetime.now(UTC) - timedelta(days=3)

    exp = Experience(
        task_id="task-hist-2",
        actions=[{"action": "read_sensor"}],
        outcome="SUCCESS",
        timestamp=past_time,
    )

    leaked_context = {
        "future_market_data": {
            "timestamp": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            "btc_price": 75000,
        }
    }

    with pytest.raises(TemporalLeakageError, match="INVARIANT 35"):
        engine.replay_experience(
            experience=exp,
            simulation_context=leaked_context,
            temporal_cutoff=cutoff,
        )


def test_consolidation_merges_redundant_lessons_cleanly():
    """INVARIANT 105: Consolidates redundant lessons without losing supporting evidence."""
    extractor = LessonExtractor()
    l1 = extractor.extract_lesson(
        statement="Always run pytest before git push",
        lesson_type=LessonType.PLANNING_PATTERN,
        source_experiences=["exp-101"],
        evidence=[{"check": "passed local tests"}],
        confidence=0.8,
    )
    l2 = extractor.extract_lesson(
        statement="Run pytest test suite before pushing commits",
        lesson_type=LessonType.PLANNING_PATTERN,
        source_experiences=["exp-102"],
        evidence=[{"check": "caught regression in auth"}],
        confidence=0.85,
    )

    merged = ExperienceConsolidator.consolidate_lessons(l1, l2)
    assert set(merged.source_experiences) == {"exp-101", "exp-102"}
    assert len(merged.evidence) == 2
    assert merged.reinforcement_count == 2
    assert l2.status == LessonStatus.SUPERSEDED
    assert l2.validity["status"] == "CONSOLIDATED"


def test_consolidation_rejects_contradictory_lessons():
    """INVARIANT 106: Contradictory lessons cannot be merged silently."""
    extractor = LessonExtractor()
    l_pos = extractor.extract_lesson(
        statement="Always use in-memory sqlite for unit tests",
        lesson_type=LessonType.PLANNING_PATTERN,
        source_experiences=["exp-201"],
        evidence=[{"speed": "fast"}],
    )
    l_neg = extractor.extract_lesson(
        statement="Never use in-memory sqlite for unit tests",
        lesson_type=LessonType.PLANNING_PATTERN,
        source_experiences=["exp-202"],
        evidence=[{"incompatibility": "jsonb types missing"}],
    )

    with pytest.raises(ContradictoryConsolidationError, match="INVARIANT 106"):
        ExperienceConsolidator.consolidate_lessons(l_pos, l_neg)
