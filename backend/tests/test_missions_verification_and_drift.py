"""Unit tests for Progress Engine, Empirical Milestone Verification, Goal Drift, and Goodhart's Law Detection (Task 66)."""

from app.missions.drift import GoalDriftDetector
from app.missions.progress import ProgressEngine
from app.missions.schemas import (
    Goal,
    Mission,
    MissionHealth,
    SuccessCriteria,
)


def test_multi_metric_progress_calculation():
    # Blended progress: 40% task ratio + 60% milestone ratio
    prog_none = ProgressEngine.calculate_progress(
        total_tasks=10, completed_tasks=0, verified_milestones=0, total_milestones=4
    )
    assert prog_none == 0.0

    prog_half = ProgressEngine.calculate_progress(
        total_tasks=10, completed_tasks=5, verified_milestones=2, total_milestones=4
    )
    # (0.5 * 0.4) + (0.5 * 0.6) = 0.2 + 0.3 = 0.5 -> 50.0%
    assert prog_half == 50.0

    prog_full = ProgressEngine.calculate_progress(
        total_tasks=10, completed_tasks=10, verified_milestones=4, total_milestones=4
    )
    assert prog_full == 100.0


def test_empirical_milestone_verification():
    # Fails if no criteria or no empirical evidence
    assert (
        ProgressEngine.verify_milestone("m1", completion_criteria=[], empirical_evidence=["log output"])
        is False
    )
    assert (
        ProgressEngine.verify_milestone("m1", completion_criteria=["tests pass"], empirical_evidence=[])
        is False
    )

    # Invariant: Each criterion must have corresponding empirical verification evidence
    criteria = ["database migrated", "latency benchmark under 50ms"]
    insufficient_evidence = ["database migrated to v16"]
    assert ProgressEngine.verify_milestone("m1", criteria, insufficient_evidence) is False

    sufficient_evidence = [
        "database migrated successfully",
        "latency benchmark under 50ms verified in production",
    ]
    assert ProgressEngine.verify_milestone("m1", criteria, sufficient_evidence) is True


def test_goal_success_evaluation():
    goal = Goal(
        title="Reduce payment failure rate",
        description="Ensure error rate is below 0.5%",
        success_criteria=[
            SuccessCriteria(
                description="Error rate under 0.5%",
                criteria_type="metric_threshold",
                target_metric="error_rate_pct",
                target_value=0.5,
                comparison_operator="lte",
            )
        ],
    )

    # Missing telemetry reading
    passed, reasons = ProgressEngine.evaluate_goal_success(goal, {})
    assert passed is False
    assert "not available" in reasons[0]

    # Telemetry reading above threshold
    passed, reasons = ProgressEngine.evaluate_goal_success(goal, {"error_rate_pct": 1.2})
    assert passed is False
    assert "did not satisfy lte 0.5" in reasons[0]

    # Telemetry reading satisfies threshold
    passed, reasons = ProgressEngine.evaluate_goal_success(goal, {"error_rate_pct": 0.3})
    assert passed is True
    assert len(reasons) == 0
    assert goal.success_criteria[0].is_verified is True


def test_sunk_cost_defense():
    # Under consecutive failures and low expected future value -> Alert triggered
    is_sunk_cost, reason = ProgressEngine.evaluate_sunk_cost(
        consecutive_failures=3,
        cost_incurred=1500.0,
        expected_future_value=0.2,
    )
    assert is_sunk_cost is True
    assert "SUNK COST ALERT" in reason

    # Still viable strategy
    is_sunk_cost_viable, reason_viable = ProgressEngine.evaluate_sunk_cost(
        consecutive_failures=1,
        cost_incurred=200.0,
        expected_future_value=0.8,
    )
    assert is_sunk_cost_viable is False
    assert "viable" in reason_viable


def test_goal_drift_detection():
    mission = Mission(
        title="Optimize database latency",
        description="Index hot tables and tune query plans",
        health=MissionHealth.HEALTHY,
    )
    goal = Goal(
        title="Optimize database latency",
        description="Index hot tables and tune query plans",
    )

    # Actions closely aligned with goal
    aligned_actions = [
        "Analyzed slow query logs for latency bottlenecks",
        "Created composite index on accounts table to lower latency",
    ]
    alert_none = GoalDriftDetector.check_goal_drift(mission, goal, aligned_actions)
    assert alert_none is None
    assert mission.health == MissionHealth.HEALTHY

    # Actions drifting to unrelated domain (e.g. rewriting marketing CSS)
    drifting_actions = [
        "Updated CSS stylesheets for marketing landing page",
        "Redesigned navigation header icons",
        "Swapped hero banner images on public website",
    ]
    alert_drift = GoalDriftDetector.check_goal_drift(mission, goal, drifting_actions)
    assert alert_drift is not None
    assert alert_drift.divergence_score > 0.75
    assert mission.health == MissionHealth.DRIFTING


def test_objective_drift_goodharts_law():
    mission = Mission(
        title="Improve infrastructure reliability",
        description="Reduce incident count and maintain system health",
        health=MissionHealth.HEALTHY,
    )
    goal = Goal(
        title="Improve infrastructure reliability",
        description="Reduce incident count and maintain system health",
    )

    # Gaming proxy (incident count suppressed by 40%), while true metric (error rate) degrades by 25%
    alert = GoalDriftDetector.detect_objective_drift(
        mission=mission,
        goal=goal,
        proxy_metric="incident_reports_filed",
        true_objective_metric="system_availability_error_rate",
        proxy_change_pct=40.0,
        true_objective_change_pct=-25.0,
    )

    assert alert is not None
    assert alert.is_objective_drift is True
    assert mission.health == MissionHealth.DRIFTING
    assert "gaming proxy" in alert.current_trajectory.lower() or "proxy" in alert.current_trajectory.lower()
