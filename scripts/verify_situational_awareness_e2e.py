"""
End-to-End Operational Verification Script for Task 99:
KAIRO Autonomous Situation Awareness, Signal Fusion & Proactive Response Orchestrator.

Verifies the 8 Core Production Integration Scenarios:
- SCENARIO 1: Multi-Dimensional Signal Ingestion & 7-Dimensional Correlation
- SCENARIO 2: 16-State Lifecycle Machine & Lineage-Preserving Merge/Split
- SCENARIO 3: Attention Engine & Knowledge Graph Subsystem Bridges
- SCENARIO 4: Proactive Response Orchestration — Happy Path (Empirically Verified Resolution)
- SCENARIO 5: Critical Invariant: EXECUTION != VERIFIED STATE (Postcondition Mismatch Failure Path)
- SCENARIO 6: Critical Invariant: EMERGENCY STOP ALWAYS WINS (Fail-Closed Safety Gate)
- SCENARIO 7: First-Class NO_ACTION Outcome with Persisted Rationale
- SCENARIO 8: Auditable Suppression & Quiet Policy Cooldown
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

# Reconfigure stdout/stderr for Windows console unicode support
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure backend directory is in sys.path
backend_path = str(Path(__file__).resolve().parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.decision.domain import DecisionOption, DecisionType
from app.execution.domain import ActionTransaction, TransactionStatus
from app.security.emergency_stop import get_emergency_stop_service
from app.situational_awareness.bridges import (
    AttentionSubsystemBridge,
    DecisionSubsystemBridge,
    EmergencyStopBridge,
    ExecutionSubsystemBridge,
    KnowledgeGraphSubsystemBridge,
    SubsystemBridges,
    WorldStateSubsystemBridge,
)
from app.situational_awareness.correlation import SignalCorrelator
from app.situational_awareness.domain import (
    CausalStatus,
    ProactivePolicyCapability,
    SignalRecord,
    SituationInterventionRecord,
    SituationLifecycleState,
    SituationRecord,
    SituationSeverity,
    SituationType,
    SourceTrustLevel,
    utc_now,
)
from app.situational_awareness.engine import SituationalAwarenessEngine
from app.situational_awareness.lifecycle import SituationLifecycleManager
from app.situational_awareness.normalization import EventNormalizer
from app.situational_awareness.orchestrator import ProactiveResponseOrchestrator
from app.situational_awareness.schemas import (
    EventIngestRequest,
    SignalIngestRequest,
)


def print_banner(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_check(name: str, passed: bool, details: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  [{status}] {name}")
    if details:
        print(f"         ↳ {details}")
    if not passed:
        raise AssertionError(f"Check failed: {name} - {details}")


# =============================================================================
# SCENARIO 1: Signal Ingestion & 7-Dimensional Correlation
# =============================================================================

def verify_scenario_1_signal_ingestion_and_correlation():
    print_banner("SCENARIO 1: Signal Ingestion & 7-Dimensional Correlation")
    normalizer = EventNormalizer()
    correlator = SignalCorrelator()
    now = utc_now()

    req = SignalIngestRequest(
        signal_type="network_packet_loss",
        source_system="edge_router_west",
        source_trust=SourceTrustLevel.VERIFIED_EXTERNAL,
        scope="datacenter_us_west",
        subject="gateway-switch-1",
        severity=SituationSeverity.HIGH,
        payload={"loss_percentage": 0.24, "target_gateway": "10.0.0.1"},
        causal_references=["switch_firmware_upgrade_v2"],
        world_state_references=["net_fabric_switch_1"],
    )

    sig1 = normalizer.normalize_signal(req)
    print_check("Signal Normalization", isinstance(sig1, SignalRecord) and sig1.subject == "gateway-switch-1", f"Signal ID: {sig1.signal_id}")

    sig2 = SignalRecord(
        signal_type="network_latency_spike",
        source_system="datadog_synthetics",
        source_trust=SourceTrustLevel.VERIFIED_EXTERNAL,
        scope="datacenter_us_west",
        subject="gateway-switch-1",
        severity=SituationSeverity.HIGH,
        timestamp=now + timedelta(seconds=20),
        causal_references=["switch_firmware_upgrade_v2"],
        world_state_references=["net_fabric_switch_1"],
    )

    res = correlator.correlate_signals(sig1, sig2)
    score, reasons = res
    print_check("7-Dimensional Correlation Affinity", score >= 0.70, f"Affinity Score: {score:.3f}, Reasons: {reasons}")

    burst_res = correlator.detect_burst_or_persistence("gateway-switch-1", now)
    print_check("Burst/Persistence Tracking", burst_res["entity_id"] == "gateway-switch-1", f"Recent signals: {burst_res['burst_count']}")


# =============================================================================
# SCENARIO 2: 16-State Lifecycle Machine & Merge/Split Lineage
# =============================================================================

def verify_scenario_2_lifecycle_state_machine_and_lineage():
    print_banner("SCENARIO 2: 16-State Operational Lifecycle & Merge/Split Lineage")
    mgr = SituationLifecycleManager()

    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="High Disk IO Contention",
        summary="NVMe storage queue saturation",
        severity=SituationSeverity.HIGH,
    )
    print_check("Situation Initialization State", sit.lifecycle_state == SituationLifecycleState.DETECTED, f"State: {sit.lifecycle_state.value}")

    # Legal progression
    mgr.transition(sit, SituationLifecycleState.CORRELATING, reason="Related signals inbound")
    mgr.transition(sit, SituationLifecycleState.FORMING, reason="Cluster boundaries identified")
    mgr.transition(sit, SituationLifecycleState.ACTIVE, reason="Confirmed operational impact")
    print_check("Valid Transition to ACTIVE", sit.lifecycle_state == SituationLifecycleState.ACTIVE, f"Version: {sit.version}")

    # Illegal transition rejection
    illegal_ok = mgr.transition(sit, SituationLifecycleState.DETECTED, reason="Backwards jump illegal")
    print_check("Illegal Transition Rejection", not illegal_ok and sit.lifecycle_state == SituationLifecycleState.ACTIVE, "State unchanged")

    # Lineage-preserving Merge
    secondary_sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="IO Read Timeout",
        summary="Secondary block storage alert",
        severity=SituationSeverity.HIGH,
    )
    merged_parent = mgr.merge_situations(
        primary_situation=sit,
        subsumed_situations=[secondary_sit],
        reason="Subsumed under primary NVMe failure",
    )
    print_check("Lineage-Preserving Merge", secondary_sit.lifecycle_state == SituationLifecycleState.MERGED and secondary_sit.situation_id in merged_parent.merged_from_ids, f"Subsumed ID: {secondary_sit.situation_id}")

    # Lineage-preserving Split
    child_specs = [
        {"title": "Storage Volume A Failure", "summary": "Volume A detached", "severity": SituationSeverity.HIGH},
        {"title": "Storage Volume B Latency", "summary": "Volume B high response time", "severity": SituationSeverity.MEDIUM},
    ]
    children = mgr.split_situation(
        parent_situation=merged_parent,
        sub_situation_specs=child_specs,
        reason="Independent volume failure domains discovered",
    )
    print_check("Lineage-Preserving Split", merged_parent.lifecycle_state == SituationLifecycleState.SPLIT and len(children) == 2, f"Child situations created: {len(children)}")


# =============================================================================
# SCENARIO 3: Attention Engine & Knowledge Graph Subsystem Bridges
# =============================================================================

def verify_scenario_3_subsystem_bridges():
    print_banner("SCENARIO 3: Attention Engine & Knowledge Graph Subsystem Bridges")
    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.ANOMALY,
        title="Payment Service Spike",
        summary="Abnormal transaction volume",
        severity=SituationSeverity.HIGH,
    )
    sit.impact = 0.9
    sit.urgency = 0.8
    sit.novelty = 0.4

    mock_attention = MagicMock()
    mock_eval = MagicMock()
    mock_eval.scores.composite_priority = 0.88
    mock_attention.evaluate_candidate.return_value = mock_eval

    mock_graph = MagicMock()
    mock_nodes = MagicMock()
    mock_graph.graph.nodes = mock_nodes

    bridges = SubsystemBridges(
        attention_service=mock_attention,
        graph_engine=mock_graph,
    )

    priority = bridges.submit_to_attention_engine(sit)
    print_check("Attention Bridge Prioritization", priority == 0.88, f"Composite Priority Score: {priority:.2f}")

    bridges.register_situation_in_knowledge_graph(sit)
    print_check("Knowledge Graph Entity Registration", mock_nodes.create_node.called, "Graph node creation called with situation metadata")


# =============================================================================
# SCENARIO 4: Proactive Response Orchestration — Happy Path (Verified Resolution)
# =============================================================================

async def verify_scenario_4_proactive_response_happy_path():
    print_banner("SCENARIO 4: Proactive Response Pipeline — Verified Resolution")
    mock_decision_service = MagicMock()
    mock_decision_record = MagicMock()
    mock_decision_record.decision_id = "dec_restart_001"
    mock_decision_record.selected_option_id = "opt_restart"
    mock_decision_record.options = [
        DecisionOption(
            option_id="opt_restart",
            title="Restart Container Pod",
            description="Perform controlled graceful restart",
            option_type=DecisionType.ACTION,
            expected_utility=0.92,
        )
    ]
    mock_decision_service.deliberate.return_value = mock_decision_record

    mock_execution_service = MagicMock()
    mock_tx = MagicMock(spec=ActionTransaction)
    mock_tx.transaction_id = "tx_k8s_restart_001"
    mock_tx.status = TransactionStatus.SUCCEEDED
    mock_execution_service.create_transaction = AsyncMock(return_value=mock_tx)

    mock_world_state = MagicMock()
    mock_world_state.verify_post_action = AsyncMock(
        return_value={
            "verified": True,
            "outcome": "ALL_POSTCONDITIONS_SATISFIED",
            "observations": {"container_status": "RUNNING", "healthcheck": "200_OK"},
        }
    )

    bridges = SubsystemBridges(
        decision=DecisionSubsystemBridge(service=mock_decision_service),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
        world_state=WorldStateSubsystemBridge(engine=mock_world_state),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Container CrashLoopBackOff",
        summary="Auth service container failing probes",
        severity=SituationSeverity.HIGH,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    print_check("Proactive Pipeline Execution", report["status"] == "RESOLVED_VERIFIED", f"Status: {report['status']}")
    print_check("Empirically Verified State", sit.lifecycle_state == SituationLifecycleState.RESOLVED and sit.resolved_at is not None, f"State: {sit.lifecycle_state.value}")
    print_check("World-State Reconciliation Status", sit.state_reconciliation_status == "VERIFIED", f"Reconciliation Status: {sit.state_reconciliation_status}")


# =============================================================================
# SCENARIO 5: Critical Invariant: EXECUTION != VERIFIED STATE
# =============================================================================

async def verify_scenario_5_execution_vs_verified_state_invariant():
    print_banner("SCENARIO 5: Invariant EXECUTION != VERIFIED STATE (Postcondition Mismatch)")
    mock_decision_service = MagicMock()
    mock_decision_record = MagicMock()
    mock_decision_record.decision_id = "dec_scale_001"
    mock_decision_record.selected_option_id = "opt_scale"
    mock_decision_record.options = [
        DecisionOption(
            option_id="opt_scale",
            title="Scale Workers",
            description="Scale to 10 instances",
            option_type=DecisionType.ACTION,
            expected_utility=0.89,
        )
    ]
    mock_decision_service.deliberate.return_value = mock_decision_record

    mock_execution_service = MagicMock()
    mock_tx = MagicMock(spec=ActionTransaction)
    mock_tx.transaction_id = "tx_scale_workers_001"
    mock_tx.status = TransactionStatus.SUCCEEDED  # Action returned success!
    mock_execution_service.create_transaction = AsyncMock(return_value=mock_tx)

    # Telemetry observes quota rejection: Only 2 instances actually started!
    mock_world_state = MagicMock()
    mock_world_state.verify_post_action = AsyncMock(
        return_value={
            "verified": False,
            "outcome": "POSTCONDITION_MISMATCH",
            "mismatches": {"worker_count": {"expected": 10, "observed": 2}},
        }
    )

    bridges = SubsystemBridges(
        decision=DecisionSubsystemBridge(service=mock_decision_service),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
        world_state=WorldStateSubsystemBridge(engine=mock_world_state),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Processing Queue Backlog",
        summary="High unprocessed job count",
        severity=SituationSeverity.HIGH,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    print_check("Postcondition Mismatch Detected", report["status"] == "FAILED_POSTCONDITION_MISMATCH", f"Report status: {report['status']}")
    print_check("EXECUTION != VERIFIED STATE Invariant Enforced", sit.lifecycle_state == SituationLifecycleState.ACTIVE and sit.resolved_at is None, f"Situation remains ACTIVE (NOT resolved). State: {sit.lifecycle_state.value}")
    print_check("Intervention Marked NOT_VERIFIED", sit.interventions[0].execution_state == "NOT_VERIFIED", f"Execution State: {sit.interventions[0].execution_state}")


# =============================================================================
# SCENARIO 6: Critical Invariant: EMERGENCY STOP ALWAYS WINS
# =============================================================================

async def verify_scenario_6_emergency_stop_fail_closed():
    print_banner("SCENARIO 6: Invariant EMERGENCY STOP ALWAYS WINS (Fail-Closed Enforcement)")
    mock_emergency_stop = MagicMock()
    mock_emergency_stop.is_stopped.return_value = True  # Emergency Stop Active!

    mock_execution_service = MagicMock()
    mock_execution_service.create_transaction = AsyncMock()

    bridges = SubsystemBridges(
        emergency_stop=EmergencyStopBridge(service=mock_emergency_stop),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Critical Database Connection Starvation",
        summary="All pool connections acquired",
        severity=SituationSeverity.CRITICAL,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    print_check("Emergency Stop Fail-Closed Gate", report["status"] == "BLOCKED_BY_EMERGENCY_STOP", f"Status: {report['status']}")
    print_check("Zero External Execution Dispatched", not mock_execution_service.create_transaction.called, "No ActionTransaction was created")
    print_check("Safety Audit Trail on Timeline", any(e.event_type == "PROACTIVE_PIPELINE_HALTED" for e in sit.timeline), "Audit timeline event recorded")


# =============================================================================
# SCENARIO 7: First-Class NO_ACTION Outcome with Persisted Rationale
# =============================================================================

async def verify_scenario_7_no_action_first_class_outcome():
    print_banner("SCENARIO 7: Invariant NO_ACTION Outcome with Persisted Rationale")
    mock_decision_service = MagicMock()
    mock_decision_record = MagicMock()
    mock_decision_record.decision_id = "dec_jitter_001"
    mock_decision_record.selected_option_id = "opt_no_action"
    mock_decision_record.options = [
        DecisionOption(
            option_id="opt_no_action",
            title="Continue Monitoring",
            description="Jitter is within normal transient SLA tolerance",
            option_type=DecisionType.NO_ACTION,
            expected_utility=0.95,
        )
    ]
    mock_decision_service.deliberate.return_value = mock_decision_record

    mock_execution_service = MagicMock()
    mock_execution_service.create_transaction = AsyncMock()

    bridges = SubsystemBridges(
        decision=DecisionSubsystemBridge(service=mock_decision_service),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.DEGRADATION,
        title="Transient Latency Bump",
        summary="p99 increased by 10ms for 15s",
        severity=SituationSeverity.LOW,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    print_check("NO_ACTION Outcome Recognized", report["status"] == "NO_ACTION", f"Status: {report['status']}")
    print_check("Zero Transactions Executed", not mock_execution_service.create_transaction.called, "No mutation initiated")
    print_check("Persisted Rationale Recorded", any(e.event_type == "NO_ACTION_DECIDED" for e in sit.timeline), f"Timeline entries: {len(sit.timeline)}")


# =============================================================================
# SCENARIO 8: Auditable Suppression & Quiet Policy Cooldown
# =============================================================================

def verify_scenario_8_auditable_suppression_and_quiet_policy():
    print_banner("SCENARIO 8: Auditable Suppression & Quiet Policy Cooldown")
    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="High CPU During Scheduled Batch Job",
        summary="Known nightly index rebuild",
        severity=SituationSeverity.MEDIUM,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    supp = mgr.suppress_situation(
        situation=sit,
        reason="Scheduled maintenance window for database index re-creation",
        suppressed_by="ops_scheduler",
        duration_seconds=7200,
    )

    print_check("Suppression Record Created", supp.is_active and sit.lifecycle_state == SituationLifecycleState.SUPPRESSED, f"Suppression ID: {supp.suppression_id}")
    print_check("Lifecycle Manager Suppression Check", mgr.is_suppressed(sit.situation_id), "is_suppressed() returns True")

    orchestrator = ProactiveResponseOrchestrator(lifecycle=mgr)
    caps = orchestrator.evaluate_proactive_capabilities(sit)
    print_check("Policy Notification Muted Under Suppression", ProactivePolicyCapability.CAN_NOTIFY not in caps, f"Active Capabilities: {[c.value for c in caps]}")


# =============================================================================
# MAIN RUNNER
# =============================================================================

async def main_async():
    print("\n" + "#" * 70)
    print("  KAIRO TASK 99: AUTONOMOUS SITUATION AWARENESS & SIGNAL FUSION SUITE")
    print("#" * 70)

    try:
        verify_scenario_1_signal_ingestion_and_correlation()
        verify_scenario_2_lifecycle_state_machine_and_lineage()
        verify_scenario_3_subsystem_bridges()
        await verify_scenario_4_proactive_response_happy_path()
        await verify_scenario_5_execution_vs_verified_state_invariant()
        await verify_scenario_6_emergency_stop_fail_closed()
        await verify_scenario_7_no_action_first_class_outcome()
        verify_scenario_8_auditable_suppression_and_quiet_policy()

        print("\n" + "=" * 70)
        print("  🎉 ALL 8 TASK 99 OPERATIONAL SCENARIOS PASSED WITH ZERO REGRESSIONS!")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"\n❌ E2E VERIFICATION FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main():
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
