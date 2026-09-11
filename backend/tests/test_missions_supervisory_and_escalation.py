"""Unit tests for Mission Supervisory Loop, Pre-Execution Staleness, Next-Action Selection, and Boundary Validation (Task 66)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.missions.safety import (
    InsufficientAuthorityError,
    MissionSafetyError,
    validate_authority_boundary,
)
from app.missions.schemas import (
    Goal,
    GoalAuthorityScope,
    Mission,
    MissionStatus,
    SuccessCriteria,
)
from app.missions.supervisor import MissionSupervisor


def test_supervisory_cycle_budget_guard():
    supervisor = MissionSupervisor()
    goal = Goal(title="Scale workers", description="Scale celery workers")
    mission = Mission(
        title="Scale workers",
        budget_limits={"max_cost_usd": 10.0},
        budget_consumed={"max_cost_usd": 15.0},  # Exceeded budget!
    )

    with pytest.raises(MissionSafetyError) as exc_info:
        supervisor.run_supervisory_cycle(
            mission=mission,
            goal=goal,
            telemetry={},
            recent_actions=[],
        )
    assert "Budget" in str(exc_info.value)


def test_supervisory_cycle_expiration_check():
    supervisor = MissionSupervisor()
    goal = Goal(title="Timebound deployment", description="Run deploy within window")
    past_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    mission = Mission(
        title="Timebound deployment",
        status=MissionStatus.RUNNING,
        expires_at=past_time,
    )

    result = supervisor.run_supervisory_cycle(
        mission=mission,
        goal=goal,
        telemetry={},
        recent_actions=[],
    )
    assert result["cycle_status"] == "EXPIRED"
    assert mission.status == MissionStatus.EXPIRED


def test_supervisory_cycle_stale_world_state_trigger():
    supervisor = MissionSupervisor()
    goal = Goal(title="Sync inventory", description="Sync warehouse inventory cache")
    mission = Mission(
        title="Sync inventory",
        status=MissionStatus.RUNNING,
    )

    result = supervisor.run_supervisory_cycle(
        mission=mission,
        goal=goal,
        telemetry={},
        recent_actions=["Fetched local cache snapshot"],
        world_state_freshness={"is_stale": True, "stale_entities": ["inventory_db"]},
    )

    assert result["cycle_status"] == "STALE_STATE_REPLAN"
    assert mission.status == MissionStatus.REPLANNING


def test_supervisory_cycle_completion_via_truth_gate():
    supervisor = MissionSupervisor()
    goal = Goal(
        title="Reach 99.9% uptime",
        description="Verify uptime target",
        success_criteria=[
            SuccessCriteria(
                description="Uptime percentage >= 99.9",
                criteria_type="metric_threshold",
                target_metric="uptime_pct",
                target_value=99.9,
                comparison_operator="gte",
            )
        ],
    )
    mission = Mission(
        title="Reach 99.9% uptime",
        status=MissionStatus.RUNNING,
    )

    result = supervisor.run_supervisory_cycle(
        mission=mission,
        goal=goal,
        telemetry={"uptime_pct": 99.95},
        recent_actions=["Monitored telemetry over 24h window"],
    )

    assert result["cycle_status"] == "COMPLETED"
    assert result["verified"] is True
    assert mission.status == MissionStatus.COMPLETED


def test_supervisory_cycle_uncertainty_triggers_research():
    supervisor = MissionSupervisor()
    goal = Goal(title="Migrate auth subsystem", description="Evaluate Keycloak vs Ory")
    mission = Mission(
        title="Migrate auth subsystem",
        status=MissionStatus.RUNNING,
    )

    # High uncertainty score (> 0.65)
    result = supervisor.run_supervisory_cycle(
        mission=mission,
        goal=goal,
        telemetry={"uncertainty_score": 0.85},
        recent_actions=["Started evaluation"],
    )

    assert result["cycle_status"] == "IN_PROGRESS"
    next_action = result["next_action"]
    assert next_action["action_name"] == "RESEARCH_UNCERTAINTY"
    assert next_action["action_type"] == "information_seeking"
    assert len(mission.checkpoints) >= 1


def test_authority_boundary_validation():
    # Read-only authority cannot execute mutations
    with pytest.raises(InsufficientAuthorityError):
        validate_authority_boundary(
            assigned_scope=GoalAuthorityScope.READ_ONLY,
            required_scope=GoalAuthorityScope.EXECUTE_LOW_RISK,
            action_name="RestartPod",
        )

    # Execute high risk cannot execute without approval
    with pytest.raises(InsufficientAuthorityError):
        validate_authority_boundary(
            assigned_scope=GoalAuthorityScope.EXECUTE_LOW_RISK,
            required_scope=GoalAuthorityScope.HIGH_IMPACT_REQUIRES_APPROVAL,
            action_name="DropProductionDatabase",
        )

    # Permitted within scope
    validate_authority_boundary(
        assigned_scope=GoalAuthorityScope.EXECUTE_LOW_RISK,
        required_scope=GoalAuthorityScope.READ_ONLY,
        action_name="GetClusterStatus",
    )
