"""Unit tests for Contradiction Engine and Temporal Validity (Task 68)."""

from datetime import UTC, datetime, timedelta

from app.memory_consolidation.contradictions import ContradictionEngine
from app.memory_consolidation.schemas import (
    ContradictionStatus,
    DurableMemory,
    FreshnessState,
    MemoryLifecycleState,
    MemoryType,
)
from app.memory_consolidation.temporal import TemporalValidityEngine


def test_contradiction_opposing_keywords():
    """Verify detection of direct opposing assertions (Spec 12)."""
    is_conflict, reason = ContradictionEngine.are_statements_conflicting(
        "The authentication service is online and healthy.",
        "The authentication service is offline due to network outage.",
    )
    assert is_conflict is True
    assert "DIRECT_OPPOSING_ASSERTIONS" in reason


def test_contradiction_environment_contextualization():
    """Verify conflicting statements in different environments are contextualized without false conflict (Spec 12)."""
    now = datetime.now(UTC)
    m_dev = DurableMemory(
        content="Microservice payment-gw runs on port 8080.",
        structured_payload={"environment": "development"},
        status=MemoryLifecycleState.ACTIVE,
        observed_at=now,
    )
    m_prod = DurableMemory(
        content="Microservice payment-gw runs on port 9090.",
        structured_payload={"environment": "production"},
        status=MemoryLifecycleState.ACTIVE,
        observed_at=now,
    )

    conflict = ContradictionEngine.analyze_conflict(m_dev, m_prod)
    assert conflict is not None
    assert conflict.status == ContradictionStatus.CONTEXTUALIZED
    assert conflict.environment_context["env_a"] == "development"
    assert conflict.environment_context["env_b"] == "production"


def test_contradiction_temporal_supersession():
    """Verify newer observation temporally supersedes older contradictory state (Spec 12)."""
    old_time = datetime.now(UTC) - timedelta(hours=4)
    new_time = datetime.now(UTC)

    m_older = DurableMemory(
        memory_id="mem_old",
        content="Service X status is offline.",
        confidence=0.8,
        status=MemoryLifecycleState.ACTIVE,
        observed_at=old_time,
    )
    m_newer = DurableMemory(
        memory_id="mem_new",
        content="Service X status is online.",
        confidence=0.9,
        status=MemoryLifecycleState.ACTIVE,
        observed_at=new_time,
    )

    conflict = ContradictionEngine.analyze_conflict(m_older, m_newer)
    assert conflict is not None
    assert conflict.status == ContradictionStatus.SUPERSEDED
    assert conflict.memory_b_id == "mem_new"


def test_unresolved_contradiction_preserves_both():
    """INVARIANT: Unresolved contradictions preserve both claims and mark conflict (Spec 12)."""
    now = datetime.now(UTC)
    m1 = DurableMemory(
        memory_id="mem_a",
        content="Database backup completed with 0 errors.",
        status=MemoryLifecycleState.ACTIVE,
        observed_at=now,
    )
    m2 = DurableMemory(
        memory_id="mem_b",
        content="Database backup completed with 12 errors.",
        status=MemoryLifecycleState.ACTIVE,
        observed_at=now,
    )

    conflict = ContradictionEngine.analyze_conflict(m1, m2)
    assert conflict is not None
    assert conflict.status == ContradictionStatus.CONFLICTED
    # Neither is deleted; both marked CONFLICTED
    assert m1.status == MemoryLifecycleState.CONFLICTED
    assert m2.status == MemoryLifecycleState.CONFLICTED


def test_temporal_validity_and_freshness():
    """Verify point-in-time validity and type-dependent freshness decay (Spec 13, 14, 15)."""
    now = datetime.now(UTC)
    m_old_working = DurableMemory(
        content="Temporary scratchpad token verification log",
        memory_type=MemoryType.WORKING_MEMORY,
        status=MemoryLifecycleState.ACTIVE,
        observed_at=now - timedelta(hours=3),  # Working memory TTL is 2h
        valid_from=now - timedelta(hours=3),
    )

    freshness = TemporalValidityEngine.evaluate_freshness(m_old_working, reference_time=now)
    assert freshness == FreshnessState.STALE

    # Priority decay
    priority = TemporalValidityEngine.calculate_decay_priority(m_old_working, reference_time=now)
    assert priority < 0.5  # Reduced retrieval priority due to staleness

    # Point-in-time validity
    assert TemporalValidityEngine.is_valid_at(m_old_working, now - timedelta(hours=2)) is True
