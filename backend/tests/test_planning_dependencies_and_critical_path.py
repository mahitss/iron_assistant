"""Unit tests for Dependency Graph, Cycle Detection, and Critical Path (CPM) (Task 58)."""

from __future__ import annotations

import pytest

from app.planning.critical_path import critical_path_engine
from app.planning.dependencies import dependency_graph_engine
from app.planning.safety import DependencyCycleError
from app.planning.schemas import PlanTask


def test_dependency_graph_linear_and_branching():
    t1 = PlanTask(title="T1", duration_expected=2.0)
    t2 = PlanTask(title="T2", dependencies=[t1.task_id], duration_expected=3.0)
    t3 = PlanTask(title="T3", dependencies=[t1.task_id], duration_expected=1.0)
    t4 = PlanTask(title="T4", dependencies=[t2.task_id, t3.task_id], duration_expected=4.0)

    tasks = [t4, t2, t1, t3]  # Out of order

    sorted_tasks = dependency_graph_engine.topological_sort(tasks)
    sorted_ids = [t.task_id for t in sorted_tasks]

    # T1 must precede T2 and T3; T2 and T3 must precede T4
    assert sorted_ids.index(t1.task_id) < sorted_ids.index(t2.task_id)
    assert sorted_ids.index(t1.task_id) < sorted_ids.index(t3.task_id)
    assert sorted_ids.index(t2.task_id) < sorted_ids.index(t4.task_id)
    assert sorted_ids.index(t3.task_id) < sorted_ids.index(t4.task_id)


def test_dependency_cycle_detection():
    t1 = PlanTask(title="T1")
    t2 = PlanTask(title="T2", dependencies=[t1.task_id])
    t3 = PlanTask(title="T3", dependencies=[t2.task_id])
    # Introduce cycle: T1 depends on T3
    t1.dependencies = [t3.task_id]

    tasks = [t1, t2, t3]

    cycle = dependency_graph_engine.detect_cycles(tasks)
    assert len(cycle) > 0

    with pytest.raises(DependencyCycleError) as exc_info:
        dependency_graph_engine.topological_sort(tasks)
    assert "Circular dependency detected" in str(exc_info.value)


def test_missing_dependency_detection():
    t1 = PlanTask(title="T1", dependencies=["missing_task_id_999"])
    valid, errors = dependency_graph_engine.validate_dependencies([t1])
    assert valid is False
    assert len(errors) == 1
    assert "references missing dependency" in errors[0]


def test_critical_path_method_cpm():
    # T1 (dur=2) -> T2 (dur=5) -> T4 (dur=3)
    # T1 (dur=2) -> T3 (dur=1) -> T4 (dur=3)
    # Critical path: T1 -> T2 -> T4 (total duration = 2 + 5 + 3 = 10.0)
    # T3 slack should be 5 - 1 = 4.0
    t1 = PlanTask(title="T1", duration_expected=2.0)
    t2 = PlanTask(title="T2", dependencies=[t1.task_id], duration_expected=5.0)
    t3 = PlanTask(title="T3", dependencies=[t1.task_id], duration_expected=1.0)
    t4 = PlanTask(title="T4", dependencies=[t2.task_id, t3.task_id], duration_expected=3.0)

    tasks = [t1, t2, t3, t4]

    cpm = critical_path_engine.compute_critical_path(tasks)

    assert cpm["total_duration"] == 10.0
    assert set(cpm["critical_task_ids"]) == {t1.task_id, t2.task_id, t4.task_id}
    assert t3.task_id not in cpm["critical_task_ids"]

    metrics = cpm["task_metrics"]
    assert metrics[t1.task_id]["early_start"] == 0.0
    assert metrics[t1.task_id]["early_finish"] == 2.0
    assert metrics[t1.task_id]["total_slack"] == 0.0
    assert metrics[t1.task_id]["is_critical"] is True

    assert metrics[t2.task_id]["early_start"] == 2.0
    assert metrics[t2.task_id]["early_finish"] == 7.0
    assert metrics[t2.task_id]["total_slack"] == 0.0
    assert metrics[t2.task_id]["is_critical"] is True

    assert metrics[t3.task_id]["early_start"] == 2.0
    assert metrics[t3.task_id]["early_finish"] == 3.0
    assert metrics[t3.task_id]["total_slack"] == 4.0
    assert metrics[t3.task_id]["is_critical"] is False

    assert metrics[t4.task_id]["early_start"] == 7.0
    assert metrics[t4.task_id]["early_finish"] == 10.0
    assert metrics[t4.task_id]["total_slack"] == 0.0
    assert metrics[t4.task_id]["is_critical"] is True

    # Sensitivity analysis
    sensitivity = cpm["sensitivity_analysis"]
    assert sensitivity["critical_task_count"] == 3
    assert sensitivity["total_task_count"] == 4
    assert sensitivity["bottlenecks"][0]["task_id"] == t2.task_id  # T2 is longest critical bottleneck
