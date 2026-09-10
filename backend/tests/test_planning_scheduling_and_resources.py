"""Unit tests for Scheduling, Execution Waves, and Resource Planning (Task 58)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.planning.resources import resource_manager
from app.planning.scheduling import scheduling_engine
from app.planning.schemas import PlanTask, ResourceRequirement, ResourceType


def test_wave_clustering_resolves_resource_conflicts():
    # T1 and T2 have no dependencies between each other (could theoretically run in parallel wave 1)
    # But both require exclusive access to 'production_db_migration_slot'
    res_exclusive = ResourceRequirement(
        resource_type=ResourceType.ENVIRONMENT,
        name="production_db_migration_slot",
        is_exclusive=True,
    )

    t1 = PlanTask(title="T1: Schema Migration", resources=[res_exclusive], duration_expected=2.0)
    t2 = PlanTask(title="T2: Index Rebuild", resources=[res_exclusive], duration_expected=3.0)

    tasks = [t1, t2]

    waves = scheduling_engine.cluster_execution_waves(tasks)

    # Must be split into 2 separate waves because of mutual exclusion!
    assert len(waves) == 2
    assert waves[0].wave_number == 1
    assert waves[0].task_ids == [t1.task_id]
    assert waves[1].wave_number == 2
    assert waves[1].task_ids == [t2.task_id]


def test_deadline_feasibility_evaluation():
    start = datetime.now(timezone.utc)
    t1 = PlanTask(title="T1", duration_expected=10.0)
    t2 = PlanTask(title="T2", dependencies=[t1.task_id], duration_expected=10.0)

    # Planned duration = 10 + 10 = 20h. Buffer 20% = 4h. Total = 24h.
    # Scenario A: Deadline 30 hours from now -> FEASIBLE
    feasible_deadline = start + timedelta(hours=30.0)
    res_a = scheduling_engine.evaluate_deadline_feasibility([t1, t2], start, feasible_deadline)
    assert res_a["is_feasible"] is True
    assert res_a["slack_hours"] == pytest.approx(6.0, 0.1)

    # Scenario B: Deadline 15 hours from now -> INFEASIBLE (deficit of 9 hours)
    infeasible_deadline = start + timedelta(hours=15.0)
    res_b = scheduling_engine.evaluate_deadline_feasibility([t1, t2], start, infeasible_deadline)
    assert res_b["is_feasible"] is False
    assert "infeasibility_details" in res_b
    assert res_b["infeasibility_details"]["deficit_hours"] == pytest.approx(9.0, 0.1)
    assert len(res_b["infeasibility_details"]["alternatives"]) > 0


def test_resource_manager_unknown_and_insufficient_resources():
    req_cpu = ResourceRequirement(name="high_mem_cpu", amount=16.0, unit="cores")
    req_unknown = ResourceRequirement(name="quantum_accelerator", amount=1.0, unit="chips")

    t1 = PlanTask(title="Heavy Compute", resources=[req_cpu, req_unknown])

    # Invariant 10: Unknown resource is not available resource
    known_system = {"high_mem_cpu": 8.0}  # Only 8 available, quantum_accelerator missing
    ok, issues = resource_manager.validate_resource_availability([t1], known_system_resources=known_system)

    assert ok is False
    assert len(issues) == 2
    assert any("UNKNOWN" in iss for iss in issues)
    assert any("insufficient capacity" in iss for iss in issues)
