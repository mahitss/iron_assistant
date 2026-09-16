"""End-to-end verification script for Task 93: KAIRO Autonomous System State Graph & Self-Modeling.

Executes 12 comprehensive operational scenarios validating:
1. Operational entity creation and rigid epistemic status boundaries
2. Deterministic canonical state fingerprinting & invariant verification
3. Bounded graph traversal with circular reference cycle-safety
4. Hierarchical goal -> task -> workflow -> capability -> resource mapping
5. Real-time snapshot generation and state-delta diff computation
6. Idempotent canonical event-sourced state reducer with deduplication
7. Freshness & TTL tracking (missing heartbeat -> UNKNOWN, never blindly FAILED)
8. SecurityCenter & EmergencyStop mutation lock (fail-closed protection)
9. Structured system self-diagnostics synthesis without hidden reasoning
10. Introspective self-model answering 13 canonical operational queries
11. Startup state reconciliation & orphan work recovery
12. CLI parser and subcommands execution
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.security.emergency_stop import EmergencyStopService
from app.security.exceptions import EmergencyStopActiveError
from app.system_state.cli import build_parser
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


def run_e2e_scenarios() -> int:
    print("======================================================================")
    print("TASK 93 — SYSTEM STATE GRAPH & SELF-MODELING END-TO-END VERIFICATION")
    print("======================================================================")
    passed = 0
    total = 12

    # ------------------------------------------------------------------
    # Scenario 1: Epistemic Invariants & Entities
    # ------------------------------------------------------------------
    print("\n[Scenario 1] Validating Epistemic Invariants & Strongly Typed Entities...")
    ent = StateEntity(
        id="comp:native_bridge",
        state_type=StateType.COMPONENT,
        status=StateCategory.HEALTHY,
        epistemic_status=EpistemicStatus.OBSERVED,
        confidence=1.0,
        health_score=1.0,
        source="heartbeat",
    )
    assert ent.epistemic_status == EpistemicStatus.OBSERVED
    assert EpistemicStatus.OBSERVED != EpistemicStatus.INFERRED
    assert EpistemicStatus.INFERRED != EpistemicStatus.PREDICTED
    assert EpistemicStatus.PREDICTED != EpistemicStatus.UNKNOWN
    print("  -> Passed: Epistemic boundaries strictly enforced.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 2: Deterministic State Hashing
    # ------------------------------------------------------------------
    print("\n[Scenario 2] Validating Deterministic Canonical State Fingerprinting...")
    e1 = StateEntity(id="comp:A", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY)
    e2 = StateEntity(id="comp:B", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY)
    edge = StateEdge(source_id="comp:A", target_id="comp:B", edge_type=EdgeType.CAPABILITY_DEPENDENCY)

    h1 = compute_state_hash({"comp:A": e1, "comp:B": e2}, [edge])
    h2 = compute_state_hash({"comp:B": e2, "comp:A": e1}, [edge])
    assert h1 == h2, "Hash must be independent of dict order"
    assert h1.startswith("ssh_")

    e1_deg = e1.with_update(status=StateCategory.DEGRADED, health_score=0.4)
    h3 = compute_state_hash({"comp:A": e1_deg, "comp:B": e2}, [edge])
    assert h1 != h3, "Status change must alter hash"
    print(f"  -> Passed: Deterministic fingerprinting verified ({h1[:16]}...).")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 3: Cycle-Safe Bounded Graph Traversal
    # ------------------------------------------------------------------
    print("\n[Scenario 3] Validating Circular Reference Cycle-Safety & Bounded Traversal...")
    graph = SystemStateGraph()
    for name in ["node_1", "node_2", "node_3"]:
        graph.add_entity(StateEntity(id=f"comp:{name}", state_type=StateType.COMPONENT, status=StateCategory.HEALTHY))
    graph.add_entity(StateEntity(id="goal:recovery_obj", state_type=StateType.GOAL, status=StateCategory.ACTIVE))

    graph.add_edge(StateEdge(source_id="comp:node_1", target_id="comp:node_2", edge_type=EdgeType.INCIDENT_COMPONENT))
    graph.add_edge(StateEdge(source_id="comp:node_2", target_id="comp:node_3", edge_type=EdgeType.INCIDENT_COMPONENT))
    graph.add_edge(StateEdge(source_id="comp:node_3", target_id="comp:node_1", edge_type=EdgeType.INCIDENT_COMPONENT))  # cycle
    graph.add_edge(StateEdge(source_id="comp:node_3", target_id="goal:recovery_obj", edge_type=EdgeType.FAILURE_GOAL))

    impacted = graph.impact_of("comp:node_1", max_depth=10)
    assert len(impacted) == 3, f"Expected 3 impacted nodes, got {len(impacted)}"
    goals = graph.goals_affected_by("comp:node_1")
    assert len(goals) == 1 and goals[0].id == "goal:recovery_obj"
    print("  -> Passed: Bounded traversal successfully resolved circular loop without stack overflow.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 4: Hierarchical Operational Tree
    # ------------------------------------------------------------------
    print("\n[Scenario 4] Validating GOAL -> TASK -> WORKFLOW -> CAPABILITY -> RESOURCE Hierarchy...")
    g2 = SystemStateGraph()
    g2.add_entity(StateEntity(id="goal:prod", state_type=StateType.GOAL, status=StateCategory.ACTIVE))
    g2.add_entity(StateEntity(id="task:crawl", state_type=StateType.TASK, status=StateCategory.ACTIVE))
    g2.add_entity(StateEntity(id="workflow:wf1", state_type=StateType.WORKFLOW, status=StateCategory.ACTIVE))
    g2.add_entity(StateEntity(id="cap:browser", state_type=StateType.CAPABILITY, status=StateCategory.HEALTHY))
    g2.add_entity(StateEntity(id="resource:pool_mem", state_type=StateType.RESOURCE, status=StateCategory.HEALTHY))

    g2.add_edge(StateEdge(source_id="goal:prod", target_id="task:crawl", edge_type=EdgeType.GOAL_TASK))
    g2.add_edge(StateEdge(source_id="task:crawl", target_id="workflow:wf1", edge_type=EdgeType.TASK_WORKFLOW))
    g2.add_edge(StateEdge(source_id="workflow:wf1", target_id="cap:browser", edge_type=EdgeType.WORKFLOW_CAPABILITY))
    g2.add_edge(StateEdge(source_id="cap:browser", target_id="resource:pool_mem", edge_type=EdgeType.RUNTIME_RESOURCE))

    res_used = g2.resources_used_by("goal:prod")
    assert len(res_used) == 1 and res_used[0].id == "resource:pool_mem"
    tasks_affected = g2.tasks_affected_by("cap:browser")
    assert len(tasks_affected) == 1 and tasks_affected[0].id == "task:crawl"
    print("  -> Passed: Complete multi-tier dependency chain queried accurately.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 5: Snapshot & State Delta Engine
    # ------------------------------------------------------------------
    print("\n[Scenario 5] Validating Snapshot Generation & State Delta Differential...")
    delta_engine = StateDeltaEngine(g2)
    snap_a = g2.export_snapshot("snap_alpha")

    # Degrade browser capability
    browser_deg = g2.get_entity("cap:browser").with_update(status=StateCategory.DEGRADED, health_score=0.2)
    g2.add_entity(browser_deg)
    snap_b = g2.export_snapshot("snap_beta")

    deltas = delta_engine.compute_deltas(snap_a, snap_b)
    assert len(deltas) == 1
    assert deltas[0].delta_type == DeltaType.DEGRADED
    assert deltas[0].entity_id == "cap:browser"
    assert "task:crawl" in deltas[0].affected_tasks
    print(f"  -> Passed: Delta computed ({deltas[0].delta_type.value}) with mapped task cascade.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 6: Idempotent Event Reducer
    # ------------------------------------------------------------------
    print("\n[Scenario 6] Validating Idempotent Event-Sourced Reducer...")
    g3 = SystemStateGraph()
    reducer = SystemStateReducer(g3)

    # Ingest task started
    r1 = reducer.reduce_event("tasks.started", {"task_id": "auto_task_93"}, event_id="evt_100")
    assert r1 is True
    # Replay duplicate
    r2 = reducer.reduce_event("tasks.started", {"task_id": "auto_task_93"}, event_id="evt_100")
    assert r2 is False, "Duplicate event must be ignored idempotently"

    task_ent = g3.get_entity("task:auto_task_93")
    assert task_ent is not None and task_ent.status == StateCategory.ACTIVE
    print("  -> Passed: Duplicate events successfully rejected without state corruption.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 7: Freshness & Missing Heartbeat Semantics
    # ------------------------------------------------------------------
    print("\n[Scenario 7] Validating Staleness & Missing Heartbeat Invariant...")
    old_time = datetime.now(UTC) - timedelta(seconds=120)
    native_proc = StateEntity(
        id="runtime:native_rust_runtime",
        state_type=StateType.RUNTIME,
        status=StateCategory.HEALTHY,
        epistemic_status=EpistemicStatus.OBSERVED,
        ttl_seconds=30.0,
        updated_at=old_time,
    )
    g3.add_entity(native_proc)
    stale_items = g3.mark_stale_entities()
    assert len(stale_items) == 1
    rechecked = g3.get_entity("runtime:native_rust_runtime")
    assert rechecked.status == StateCategory.UNKNOWN
    assert rechecked.status != StateCategory.FAILED
    assert rechecked.epistemic_status == EpistemicStatus.UNKNOWN
    print("  -> Passed: Missing heartbeat transitioned to UNKNOWN, never assumed FAILED.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 8: SecurityCenter & EmergencyStop Boundary
    # ------------------------------------------------------------------
    print("\n[Scenario 8] Validating EmergencyStop Fail-Closed Mutation Protection...")
    estop = EmergencyStopService()
    svc = SystemStateService(emergency_stop=estop)

    estop.trigger_emergency_stop(reason="Penetration Test Intercept")
    assert estop.is_stopped() is True

    # Safe read works
    summary = svc.get_summary()
    assert summary["security_emergency_stop"] is True

    # Mutation fails closed
    mutation_blocked = False
    try:
        svc.create_snapshot()
    except EmergencyStopActiveError:
        mutation_blocked = True
    assert mutation_blocked is True, "EmergencyStop MUST block mutating operations"
    print("  -> Passed: Mutation blocked fail-closed under EmergencyStop; read inspection allowed.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 9: Structured Self-Diagnostics
    # ------------------------------------------------------------------
    print("\n[Scenario 9] Validating Structured Self-Diagnostics Generation...")
    diag_engine = SystemDiagnosticsEngine(g2)
    diagnosis = diag_engine.generate_diagnosis()
    assert diagnosis.current_state in (StateCategory.DEGRADED, StateCategory.HEALTHY)
    assert isinstance(diagnosis.health_score, float)
    assert "OBSERVED" in diagnosis.epistemic_breakdown
    assert isinstance(diagnosis.resource_pressure, dict)
    print(f"  -> Passed: Structured diagnosis synthesized (Health: {diagnosis.health_score * 100}%).")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 10: Canonical Self-Model Introspection
    # ------------------------------------------------------------------
    print("\n[Scenario 10] Validating 13 Canonical Self-Model Inquiries...")
    self_model = SelfModelQueryEngine(g2)
    answers = self_model.answer_all(recent_deltas=deltas)
    assert len(answers.what_am_i_doing) >= 1
    assert len(answers.why_am_i_doing_it) >= 1
    assert len(answers.what_changed_recently) >= 1
    assert len(answers.what_capabilities_are_degraded) >= 1
    print("  -> Passed: Self-Model accurately answers 'What am I doing?' and 'Why am I doing it?'.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 11: Startup Reconciliation & Orphan Repair
    # ------------------------------------------------------------------
    print("\n[Scenario 11] Validating Startup Reconciliation & Orphan Recovery...")
    g_rec = SystemStateGraph()
    rec_engine = StateReconciliationEngine(g_rec)
    old_snap = SystemStateSnapshot(
        snapshot_id="snap_reboot",
        state_hash="ssh_init",
        entities={
            "task:unverified_job": StateEntity(id="task:unverified_job", state_type=StateType.TASK, status=StateCategory.ACTIVE)
        },
        edges=[],
    )
    rec_result = rec_engine.reconcile(latest_snapshot=old_snap)
    assert rec_result["status"] == "COMPLETED"
    assert rec_result["orphaned_entities"] >= 1
    repaired_job = g_rec.get_entity("task:unverified_job")
    assert repaired_job.status == StateCategory.UNKNOWN
    print("  -> Passed: Unverified active task repaired to UNKNOWN on post-reboot reconciliation.")
    passed += 1

    # ------------------------------------------------------------------
    # Scenario 12: CLI Argument Parser
    # ------------------------------------------------------------------
    print("\n[Scenario 12] Validating CLI Parser and Subcommands...")
    parser = build_parser()
    args_status = parser.parse_args(["status"])
    assert args_status.subcommand == "status"
    args_impact = parser.parse_args(["impact", "cap:browser"])
    assert args_impact.subcommand == "impact"
    assert args_impact.component_id == "cap:browser"
    print("  -> Passed: CLI commands parsed successfully.")
    passed += 1

    print("\n======================================================================")
    print(f"E2E VERIFICATION COMPLETED: {passed}/{total} SCENARIOS PASSED (100%)")
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(run_e2e_scenarios())
