"""Unit tests for Goal Modeling, Normalization, Ambiguity Detection, Feasibility, Conflicts, and DAG Management (Task 66)."""

from datetime import datetime, timezone

import pytest

from app.missions.goals import GoalManager
from app.missions.safety import MissionSafetyError
from app.missions.schemas import (
    Goal,
    GoalAuthorityScope,
    GoalFeasibilityStatus,
    GoalOrigin,
    GoalValidationStatus,
)


def test_goal_normalization_structured_parsing():
    manager = GoalManager()
    raw = "Reduce API latency without hurting reliability"
    goal, status, ambiguity = manager.normalize_goal(
        raw_objective=raw,
        origin=GoalOrigin.USER,
        authority_scope=GoalAuthorityScope.EXECUTE_LOW_RISK,
        owner="test_user",
        tenant_id="tenant_alpha",
    )

    assert status == GoalValidationStatus.VALID
    assert "latency" in goal.title.lower()
    assert len(goal.constraints) >= 1
    assert any("reliability" in c.lower() for c in goal.constraints)
    assert len(goal.success_criteria) >= 1
    assert goal.success_criteria[0].target_metric == "p95_latency_ms"
    assert goal.owner == "test_user"
    assert goal.tenant_id == "tenant_alpha"


def test_goal_normalization_ambiguity_detection():
    manager = GoalManager()
    # Ambiguous, under-specified objective with vague terms and no quantifiable metrics
    vague_raw = "Make the system better"
    goal, status, ambiguity = manager.normalize_goal(raw_objective=vague_raw)

    assert status == GoalValidationStatus.NEEDS_CLARIFICATION
    assert "ambiguity_reason" in ambiguity
    assert len(ambiguity.get("candidate_interpretations", [])) >= 3
    assert "suggested_defaults" in ambiguity


def test_goal_validation_checks():
    manager = GoalManager()
    # Valid goal
    valid_goal = Goal(
        title="Migrate database cluster",
        description="Migrate Postgres from v14 to v16 with minimal downtime",
        success_criteria=[
            {
                "description": "Database version is 16",
                "criteria_type": "verification_result",
            }
        ],
    )
    assert manager.validate_goal(valid_goal) == GoalValidationStatus.VALID

    # Invalid goal without success criteria
    invalid_goal = Goal(
        title="Unspecified objective",
        description="Doing something without criteria",
        success_criteria=[],
    )
    assert manager.validate_goal(invalid_goal) == GoalValidationStatus.NEEDS_CLARIFICATION


def test_goal_feasibility_estimation():
    manager = GoalManager()
    goal = Goal(
        title="Deploy edge cache",
        description="Deploy Cloudflare Workers cache layer",
        resources=["cloud_credentials", "dns_access"],
        risk_level=0.3,
        deadline=datetime.now(timezone.utc),
    )

    # Missing resources -> BLOCKED
    status, reason = manager.estimate_feasibility(goal, available_resources=["cloud_credentials"])
    assert status == GoalFeasibilityStatus.BLOCKED
    assert "Missing required resources" in reason

    # High risk or active environmental risks -> INFEASIBLE
    status, reason = manager.estimate_feasibility(
        goal,
        available_resources=["cloud_credentials", "dns_access"],
        world_risks=["active_ddos", "datacenter_power_failure", "isp_outage"],
    )
    assert status == GoalFeasibilityStatus.INFEASIBLE

    # All resources available with minimal risks -> FEASIBLE
    status, reason = manager.estimate_feasibility(
        goal,
        available_resources=["cloud_credentials", "dns_access"],
        world_risks=[],
    )
    assert status in (GoalFeasibilityStatus.FEASIBLE, GoalFeasibilityStatus.LIKELY_FEASIBLE)


def test_goal_conflict_detection():
    manager = GoalManager()
    goal_cost = Goal(
        title="Reduce infrastructure cost",
        description="Cut spend across all compute clusters by 40%",
        resources=["k8s_cluster"],
    )
    goal_redundancy = Goal(
        title="Increase redundancy",
        description="Provision multi-region standby clusters in 3 regions",
        resources=["k8s_cluster"],
    )

    conflict = manager.detect_conflicts(goal_cost, goal_redundancy)
    assert conflict is not None
    assert len(conflict.conflicting_goal_ids) == 2
    assert len(conflict.tradeoffs) >= 1
    assert "cost" in conflict.tradeoffs[0].lower() or "redundancy" in conflict.tradeoffs[0].lower()

    # Latency vs Thorough Security Audit
    goal_latency = Goal(
        title="Minimize latency",
        description="Minimize latency for real-time payments API",
    )
    goal_audit = Goal(
        title="Deep security inspection",
        description="Perform deep inspection and full payload audit on all ingress",
    )
    conflict2 = manager.detect_conflicts(goal_latency, goal_audit)
    assert conflict2 is not None
    assert "inspection" in conflict2.tradeoffs[0].lower()


def test_goal_dag_dependencies_and_cycle_prevention():
    manager = GoalManager()
    g1, _, _ = manager.normalize_goal("Step 1: Setup staging environment")
    g2, _, _ = manager.normalize_goal("Step 2: Run migration scripts")
    g3, _, _ = manager.normalize_goal("Step 3: Verify data integrity")

    # Valid chain: g1 -> g2 -> g3
    manager.add_dependency(g1.goal_id, g2.goal_id)
    manager.add_dependency(g2.goal_id, g3.goal_id)

    # Self dependency should fail
    with pytest.raises(MissionSafetyError):
        manager.add_dependency(g1.goal_id, g1.goal_id)

    # Cycle creation: g3 -> g1 should be blocked!
    with pytest.raises(MissionSafetyError) as exc_info:
        manager.add_dependency(g3.goal_id, g1.goal_id)
    assert "Circular dependency" in str(exc_info.value)


def test_goal_priority_calculation():
    manager = GoalManager()
    high_prio_goal = Goal(
        title="P0 Incident Mitigation",
        description="Mitigate ongoing service outage",
        importance=0.9,
        urgency=0.9,
        risk_level=0.2,
        priority=9,
    )
    low_prio_goal = Goal(
        title="Backlog documentation cleanup",
        description="Format markdown docs",
        importance=0.2,
        urgency=0.1,
        risk_level=0.1,
        priority=2,
    )

    score_high = manager.calculate_priority_score(high_prio_goal)
    score_low = manager.calculate_priority_score(low_prio_goal)

    assert score_high > score_low
    assert 0.0 <= score_high <= 1.0
    assert 0.0 <= score_low <= 1.0
