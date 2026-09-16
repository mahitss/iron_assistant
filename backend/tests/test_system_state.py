"""Comprehensive test suite for Task 93: KAIRO System State Graph, Self-Modeling & Operational Digital Twin.

Verifies:
- Epistemic invariants (OBSERVED != INFERRED != PREDICTED != UNKNOWN)
- Missing heartbeats -> UNKNOWN / STALE, never FAILED without evidence
- Deterministic canonical state hashing and property testing
- Bounded graph traversal, cycle protection, and impact queries
- State delta computation and cascading impact mapping
- Idempotent event reduction & deduplication
- EmergencyStop fail-closed mutation protection
- Structured diagnostics & introspective self-model questions
- Startup reconciliation & orphaned work repair
"""

from datetime import UTC, datetime, timedelta
import pytest

from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError
from app.system_state.delta import StateDeltaEngine
from app.system_state.diagnostics import SystemDiagnosticsEngine
from app.system_state.graph import SystemStateGraph
from app.system_state.hasher import compute_state_hash
from app.system_state.models import (
    DeltaType,
    EdgeType,
    EpistemicStatus,
    StateCategory,
    StateEdge,
    StateEntity,
    StateType,
    SystemStateSnapshot,
)
from app.system_state.reconciliation import StateReconciliationEngine
from app.system_state.reducer import SystemStateReducer
from app.system_state.self_model import SelfModelQueryEngine
from app.system_state.service import SystemStateService


# ==============================================================================
# Phase 1, 2, 3: Entity Creation & Epistemic Invariants
# ==============================================================================


def test_entity_creation_and_epistemic_statuses():
    ent = StateEntity(
        id="task:test_1",
        state_type=StateType.TASK,
        status=StateCategory.ACTIVE,
        epistemic_status=EpistemicStatus.OBSERVED,
        confidence=1.0,
        health_score=0.95,
        source="task_engine",
    )
    assert ent.id == "task:test_1"
    assert ent.epistemic_status == EpistemicStatus.OBSERVED
    assert ent.status == StateCategory.ACTIVE

    # Ensure Epistemic enums are strictly distinct
    assert EpistemicStatus.OBSERVED != EpistemicStatus.INFERRED
    assert EpistemicStatus.INFERRED != EpistemicStatus.PREDICTED
    assert EpistemicStatus.PREDICTED != EpistemicStatus.DERIVED
    assert EpistemicStatus.UNKNOWN != EpistemicStatus.OBSERVED


def test_missing_heartbeat_transitions_to_unknown_not_failed():
    past = datetime.now(UTC) - timedelta(seconds=120)
    runtime = StateEntity(
        id="runtime:rust_worker_1",
        state_type=StateType.RUNTIME,
        status=StateCategory.HEALTHY,
        epistemic_status=EpistemicStatus.OBSERVED,
        ttl_seconds=30.0,
        updated_at=past,
    )
    assert runtime.is_stale() is True

    graph = SystemStateGraph()
    graph.add_entity(runtime)

    # Invariant: Never assume FAILED without evidence. Transition to UNKNOWN / STALE.
    stale_list = graph.mark_stale_entities()
    assert len(stale_list) == 1
    updated = graph.get_entity("runtime:rust_worker_1")
    assert updated is not None
    assert updated.status == StateCategory.UNKNOWN
    assert updated.status != StateCategory.FAILED
    assert updated.epistemic_status == EpistemicStatus.UNKNOWN


# ==============================================================================
# Phase 4 & 16: Graph Traversal, Cycles & Bounded Queries
# ==============================================================================


def test_graph_cycle_protection_and_impact():
    graph = SystemStateGraph()

    # Create cycle: A -> B -> C -> A
    ent_a = StateEntity(id="comp:A", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY)
    ent_b = StateEntity(id="comp:B", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY)
    ent_c = StateEntity(id="comp:C", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY)
    goal = StateEntity(id="goal:main", state_type=StateType.GOAL, status=StateCategory.ACTIVE)

    graph.add_entity(ent_a)
    graph.add_entity(ent_b)
    graph.add_entity(ent_c)
    graph.add_entity(goal)

    graph.add_edge(StateEdge(source_id="comp:A", target_id="comp:B", edge_type=EdgeType.INCIDENT_COMPONENT))
    graph.add_edge(StateEdge(source_id="comp:B", target_id="comp:C", edge_type=EdgeType.INCIDENT_COMPONENT))
    graph.add_edge(StateEdge(source_id="comp:C", target_id="comp:A", edge_type=EdgeType.INCIDENT_COMPONENT))
    graph.add_edge(StateEdge(source_id="comp:C", target_id="goal:main", edge_type=EdgeType.FAILURE_GOAL))

    # impact_of should terminate cleanly despite circular topology
    impacted = graph.impact_of("comp:A", max_depth=10)
    impacted_ids = {e.id for e in impacted}
    assert "comp:B" in impacted_ids
    assert "comp:C" in impacted_ids
    assert "goal:main" in impacted_ids

    # Check goal-specific query
    goals = graph.goals_affected_by("comp:A")
    assert len(goals) == 1
    assert goals[0].id == "goal:main"


def test_hierarchical_operational_mapping():
    graph = SystemStateGraph()

    goal = StateEntity(id="goal:g1", state_type=StateType.GOAL, status=StateCategory.ACTIVE)
    task = StateEntity(id="task:t1", state_type=StateType.TASK, status=StateCategory.ACTIVE)
    wf = StateEntity(id="workflow:w1", state_type=StateType.WORKFLOW, status=StateCategory.ACTIVE)
    cap = StateEntity(id="cap:c1", state_type=StateType.CAPABILITY, status=StateCategory.HEALTHY)
    res = StateEntity(id="resource:r1", state_type=StateType.RESOURCE, status=StateCategory.HEALTHY)

    for e in (goal, task, wf, cap, res):
        graph.add_entity(e)

    # Hierarchy: GOAL -> TASK -> WORKFLOW -> CAPABILITY -> RESOURCE
    graph.add_edge(StateEdge(source_id="goal:g1", target_id="task:t1", edge_type=EdgeType.GOAL_TASK))
    graph.add_edge(StateEdge(source_id="task:t1", target_id="workflow:w1", edge_type=EdgeType.TASK_WORKFLOW))
    graph.add_edge(StateEdge(source_id="workflow:w1", target_id="cap:c1", edge_type=EdgeType.WORKFLOW_CAPABILITY))
    graph.add_edge(StateEdge(source_id="cap:c1", target_id="resource:r1", edge_type=EdgeType.RUNTIME_RESOURCE))

    resources = graph.resources_used_by("goal:g1")
    assert len(resources) == 1
    assert resources[0].id == "resource:r1"

    # Tasks affected by capability failure
    affected_tasks = graph.tasks_affected_by("cap:c1")
    assert any(t.id == "task:t1" for t in affected_tasks)


# ==============================================================================
# Phase 6: Deterministic State Hashing (Property Invariants)
# ==============================================================================


def test_deterministic_state_hashing():
    e1 = StateEntity(id="comp:x", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY)
    e2 = StateEntity(id="comp:y", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY)
    edge = StateEdge(source_id="comp:x", target_id="comp:y", edge_type=EdgeType.CAPABILITY_DEPENDENCY)

    # 1. Same state produces exact same hash
    h1 = compute_state_hash({"comp:x": e1, "comp:y": e2}, [edge])
    h2 = compute_state_hash({"comp:y": e2, "comp:x": e1}, [edge])  # Reversed insertion order
    assert h1 == h2
    assert h1.startswith("ssh_")

    # 2. Meaningful operational status change alters hash
    e1_degraded = e1.with_update(status=StateCategory.DEGRADED, health_score=0.4)
    h3 = compute_state_hash({"comp:x": e1_degraded, "comp:y": e2}, [edge])
    assert h1 != h3

    # 3. Volatile non-operational metadata does NOT alter hash
    e1_with_trace = e1.with_update(metadata={"trace_id": "ephemeral_12345"})
    h4 = compute_state_hash({"comp:x": e1_with_trace, "comp:y": e2}, [edge])
    assert h1 == h4


# ==============================================================================
# Phase 7: State Delta Engine
# ==============================================================================


def test_delta_engine_computations():
    graph = SystemStateGraph()
    delta_engine = StateDeltaEngine(graph)

    # Snapshot 1: Healthy capability
    e1 = StateEntity(id="cap:search", state_type=StateType.CAPABILITY, status=StateCategory.HEALTHY)
    snap1 = graph.export_snapshot(snapshot_id="snap_1")

    # Update to degraded
    graph.add_entity(e1)
    snap1 = graph.export_snapshot(snapshot_id="snap_1")

    e1_deg = e1.with_update(status=StateCategory.DEGRADED, health_score=0.3)
    graph.add_entity(e1_deg)
    snap2 = graph.export_snapshot(snapshot_id="snap_2")

    deltas = delta_engine.compute_deltas(snap1, snap2)
    assert len(deltas) == 1
    assert deltas[0].delta_type == DeltaType.DEGRADED
    assert deltas[0].entity_id == "cap:search"
    assert deltas[0].from_status == StateCategory.HEALTHY
    assert deltas[0].to_status == StateCategory.DEGRADED


# ==============================================================================
# Phase 8: Idempotent Event Reducer
# ==============================================================================


def test_event_reducer_idempotency_and_types():
    graph = SystemStateGraph()
    reducer = SystemStateReducer(graph)

    payload = {"task_id": "task_abc", "goal_id": "goal_123"}

    # First event application
    res1 = reducer.reduce_event("task.started", payload, event_id="evt_001", sequence_num=10)
    assert res1 is True
    assert graph.get_entity("task:task_abc") is not None
    assert graph.get_entity("task:task_abc").status == StateCategory.ACTIVE

    # Duplicate event application must be idempotent (no-op)
    res2 = reducer.reduce_event("task.started", payload, event_id="evt_001", sequence_num=10)
    assert res2 is False

    # Complete task
    reducer.reduce_event("task.completed", payload, event_id="evt_002", sequence_num=11)
    completed_task = graph.get_entity("task:task_abc")
    assert completed_task.status == StateCategory.HEALTHY
    assert completed_task.health_score == 1.0


# ==============================================================================
# Phase 13 & 32: EmergencyStop Fail-Closed Boundary
# ==============================================================================


def test_emergency_stop_mutation_protection():
    emergency_stop = EmergencyStopService()
    service = SystemStateService(emergency_stop=emergency_stop)

    # Normal inspection allowed
    summary = service.get_summary()
    assert summary["overall_state"] in ("HEALTHY", "ACTIVE")

    # Trigger EmergencyStop
    emergency_stop.trigger_emergency_stop(reason="Security Incident Test")
    assert emergency_stop.is_stopped() is True

    # Safe read inspection remains functional
    safe_summary = service.get_summary()
    assert safe_summary["security_emergency_stop"] is True

    # Mutating operation MUST raise EmergencyStopActiveError
    with pytest.raises(EmergencyStopActiveError):
        service.create_snapshot()

    with pytest.raises(EmergencyStopActiveError):
        service.reconcile()


# ==============================================================================
# Phase 17 & 18: Structured Diagnostics & Self-Model Queries
# ==============================================================================


def test_structured_diagnostics_and_self_model():
    graph = SystemStateGraph()
    # Add active goal, task, and resource
    goal = StateEntity(id="goal:g1", state_type=StateType.GOAL, status=StateCategory.ACTIVE)
    task = StateEntity(id="task:t1", state_type=StateType.TASK, status=StateCategory.ACTIVE)
    graph.add_entity(goal)
    graph.add_entity(task)
    graph.add_edge(StateEdge(source_id="goal:g1", target_id="task:t1", edge_type=EdgeType.GOAL_TASK))

    diag_engine = SystemDiagnosticsEngine(graph)
    diag = diag_engine.generate_diagnosis()

    assert diag.current_state in (StateCategory.HEALTHY, StateCategory.ACTIVE)
    assert len(diag.active_objectives) == 1
    assert len(diag.active_work) == 1
    assert diag.health_score >= 0.9

    self_model = SelfModelQueryEngine(graph)
    answers = self_model.answer_all()

    # Answers Kairo's canonical questions:
    assert len(answers.what_am_i_doing) == 1
    assert answers.what_am_i_doing[0]["entity_id"] == "task:t1"

    # Why am I doing it (maps to goal:g1)
    assert len(answers.why_am_i_doing_it) == 1
    assert answers.why_am_i_doing_it[0]["work_id"] == "task:t1"


# ==============================================================================
# Phase 21: Startup Reconciliation & Orphan Repair
# ==============================================================================


def test_startup_reconciliation():
    graph = SystemStateGraph()
    reconciliation = StateReconciliationEngine(graph)

    # Simulated previous snapshot with unverified active task
    old_task = StateEntity(id="task:old_active", state_type=StateType.TASK, status=StateCategory.ACTIVE)
    snap = SystemStateSnapshot(
        snapshot_id="snap_prev",
        state_hash="ssh_dummy",
        entities={"task:old_active": old_task},
        edges=[],
    )

    result = reconciliation.reconcile(latest_snapshot=snap)
    assert result["status"] == "COMPLETED"
    assert result["orphaned_entities"] >= 1

    # Active work from old snapshot must be recovered as UNKNOWN, never assumed still active
    repaired_task = graph.get_entity("task:old_active")
    assert repaired_task is not None
    assert repaired_task.status == StateCategory.UNKNOWN
    assert repaired_task.epistemic_status == EpistemicStatus.UNKNOWN
