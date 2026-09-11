"""Unit tests for Blocker Management, Prioritization, Escalation, and Recovery Workflows (Task 66)."""

import pytest

from app.missions.blockers import BlockerManager
from app.missions.schemas import (
    Blocker,
    BlockerSeverity,
    BlockerStatus,
    Mission,
    MissionHealth,
    MissionStatus,
)


def test_blocker_registration_and_mission_state():
    manager = BlockerManager()
    mission = Mission(
        title="Deploy multi-cluster Redis",
        status=MissionStatus.RUNNING,
        health=MissionHealth.HEALTHY,
    )

    blocker = manager.register_blocker(
        mission=mission,
        blocker_type="MISSING_CREDENTIALS",
        description="AWS KMS decryption key access denied for staging vault",
        severity=BlockerSeverity.CRITICAL,
        impact_score=0.95,
    )

    assert blocker.blocker_id.startswith("blk_")
    assert blocker.status == BlockerStatus.DETECTED
    assert mission.health == MissionHealth.BLOCKED
    assert mission.status == MissionStatus.BLOCKED
    assert len(mission.blockers) == 1


def test_blocker_resolution():
    manager = BlockerManager()
    mission = Mission(title="Test mission", status=MissionStatus.RUNNING)
    blocker = manager.register_blocker(
        mission=mission,
        blocker_type="NETWORK_TIMEOUT",
        description="Temporary egress gateway latency spike",
        severity=BlockerSeverity.MEDIUM,
    )

    resolved = manager.resolve_blocker(
        blocker_id=blocker.blocker_id,
        resolution_notes="Gateway routing refreshed, latency returned to normal",
    )
    assert resolved.status == BlockerStatus.RESOLVED
    assert resolved.resolution is not None
    assert resolved.resolved_at is not None

    # Resolving non-existent blocker raises KeyError
    with pytest.raises(KeyError):
        manager.resolve_blocker("invalid_blk_id", "notes")


def test_blocker_prioritization_ranking():
    manager = BlockerManager()
    b_low = Blocker(
        mission_id="msn_1",
        blocker_type="LINT_WARNING",
        description="Minor formatting inconsistency",
        severity=BlockerSeverity.LOW,
        impact_score=0.2,
    )
    b_med = Blocker(
        mission_id="msn_1",
        blocker_type="RATE_LIMIT",
        description="API rate limit throttled for 10s",
        severity=BlockerSeverity.MEDIUM,
        impact_score=0.5,
    )
    b_crit = Blocker(
        mission_id="msn_1",
        blocker_type="DATA_CORRUPTION",
        description="Database transaction integrity failure",
        severity=BlockerSeverity.CRITICAL,
        impact_score=1.0,
    )

    ranked = manager.prioritize_blockers([b_med, b_low, b_crit])
    assert ranked[0].severity == BlockerSeverity.CRITICAL
    assert ranked[1].severity == BlockerSeverity.MEDIUM
    assert ranked[2].severity == BlockerSeverity.LOW


def test_human_escalation_generation():
    manager = BlockerManager()
    mission = Mission(
        title="Provision high-throughput GPU cluster",
        status=MissionStatus.RUNNING,
    )
    blocker = manager.register_blocker(
        mission=mission,
        blocker_type="QUOTA_EXCEEDED",
        description="Cloud provider H100 quota exceeded in us-east-1",
        severity=BlockerSeverity.HIGH,
    )

    escalation = manager.generate_human_escalation(
        mission=mission,
        blocker=blocker,
        options=[
            "Request quota increase from cloud support",
            "Failover to us-west-2 region",
            "Downscale to A100 instances",
        ],
        recommended_action="Failover to us-west-2 region where quota is available",
    )

    assert escalation["escalation_id"].startswith("esc_")
    assert escalation["mission_id"] == mission.mission_id
    assert blocker.status == BlockerStatus.ESCALATED
    assert mission.status == MissionStatus.ESCALATED
    assert len(escalation["options"]) == 3
    assert "failover" in escalation["recommended_action"].lower()
