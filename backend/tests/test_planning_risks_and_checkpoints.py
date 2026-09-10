"""Unit tests for Plan Risks, Failure Propagation, and Checkpoints (Task 58)."""

from __future__ import annotations

from app.planning.checkpoints import checkpoint_engine
from app.planning.risks import plan_risk_engine
from app.planning.schemas import (
    PlanCheckpoint,
    PlanMilestone,
    PlanTask,
    RiskSeverity,
    StrategyOption,
    StrategyType,
)


def test_plan_risk_engine_evaluation_and_irreversible_tasks():
    strategy = StrategyOption(
        name="Big Bang Switchover",
        strategy_type=StrategyType.BIG_BANG,
        description="Direct full-cutover",
        rationale="Speed",
        expected_risk=RiskSeverity.CRITICAL,
    )

    t1 = PlanTask(title="Data Purge", is_irreversible=True)
    t2 = PlanTask(title="Standard Task", is_irreversible=False)
    m1 = PlanMilestone(name="M1", dependencies=["dep1", "dep2", "dep3"])  # Fan-in >= 3

    risks = plan_risk_engine.evaluate_plan_risks(strategy, [t1, t2], [m1])

    descriptions = [r.description for r in risks]
    assert any("High strategic risk" in d for d in descriptions)
    assert any("Irreversible task action" in d for d in descriptions)
    assert any("high dependency fan-in" in d for d in descriptions)

    rollback = plan_risk_engine.generate_rollback_strategy([t1, t2])
    assert rollback["is_fully_reversible"] is False
    assert any("Irreversible tasks present" in step for step in rollback["steps"])


def test_risk_propagation_on_task_failure():
    t1 = PlanTask(title="T1: Baseline Core")
    t2 = PlanTask(title="T2: Middle Tier", dependencies=[t1.task_id])
    t3 = PlanTask(title="T3: UI Client", dependencies=[t2.task_id])
    t_other = PlanTask(title="Independent Task")

    m1 = PlanMilestone(name="Milestone Alpha", dependencies=[t3.task_id])

    impact = plan_risk_engine.propagate_task_failure_impact(
        failed_task_id=t1.task_id,
        tasks=[t1, t2, t3, t_other],
        milestones=[m1],
    )

    assert impact["failed_task_id"] == t1.task_id
    assert set(impact["impacted_task_ids"]) == {t2.task_id, t3.task_id}
    assert t_other.task_id not in impact["impacted_task_ids"]
    assert "Milestone Alpha" in impact["impacted_milestones"]


def test_checkpoint_variance_and_stopping_rules():
    # Expected metrics
    expected = {"latency_ms": 50.0, "error_count": 0, "status": "ok"}

    cp = PlanCheckpoint(name="CP-Alpha", expected_state=expected)

    # 1. Nominal observed state (variance ~ 0.0) -> CONTINUE
    obs_nominal = {"latency_ms": 50.0, "error_count": 0, "status": "ok"}
    cp_res = checkpoint_engine.evaluate_checkpoint(cp, obs_nominal)
    assert cp_res.variance_score == 0.0
    assert cp_res.decision_action == "CONTINUE"

    # 2. Mild discrepancy -> PAUSE
    obs_mild = {"latency_ms": 65.0, "error_count": 0, "status": "ok"}
    cp_res = checkpoint_engine.evaluate_checkpoint(cp, obs_mild)
    assert cp_res.decision_action in ("CONTINUE", "PAUSE")

    # 3. Moderate discrepancy -> REPLAN
    obs_mod = {"latency_ms": 150.0, "error_count": 5, "status": "ok"}
    cp_res = checkpoint_engine.evaluate_checkpoint(cp, obs_mod)
    assert cp_res.decision_action in ("PAUSE", "REPLAN")

    # 4. Severe discrepancy -> ROLLBACK
    obs_severe = {"latency_ms": 500.0, "error_count": 999, "status": "crashed"}
    cp_res = checkpoint_engine.evaluate_checkpoint(cp, obs_severe)
    assert cp_res.variance_score > 0.70
    assert cp_res.decision_action == "ROLLBACK"
