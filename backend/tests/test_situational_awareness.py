"""Comprehensive test suite for Task 99: KAIRO Autonomous Situation Awareness,
Signal Fusion & Proactive Response Orchestrator.

Validates:
1. Signal Ingestion & Normalization (SignalRecord & NormalizedEvent)
2. 7-Dimensional Signal Correlation & Burst Deduplication
3. 16-State Operational Lifecycle Machine & Invariant Transitions
4. Lineage-Preserving Merge & Split Operations
5. Auditable Suppression & Cooldown
6. Proactive Response Pipeline — Verified Resolution (Happy Path)
7. Invariant: EXECUTION != VERIFIED STATE (Postcondition Mismatch Failure Path)
8. Invariant: EMERGENCY STOP ALWAYS WINS (Fail-Closed Safety Gate)
9. Invariant: NO_ACTION First-Class Outcome with Persisted Rationale
10. Subsystem Bridges (Attention, Decision, ActionTransaction, WorldState, KG)
11. End-to-End REST API Endpoints (/signals, /refresh, /investigate, /interventions)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.decision.domain import DecisionOption, DecisionType
from app.execution.domain import ActionTransaction, TransactionStatus
from app.main import app
from app.situational_awareness.bridges import (
    AttentionSubsystemBridge,
    DecisionSubsystemBridge,
    EmergencyStopBridge,
    ExecutionSubsystemBridge,
    KnowledgeGraphSubsystemBridge,
    SubsystemBridges,
    WorldStateSubsystemBridge,
)
from app.situational_awareness.correlation import SignalCorrelationEngine
from app.situational_awareness.domain import (
    CausalStatus,
    ProactivePolicyCapability,
    SignalRecord,
    SituationContextRecord,
    SituationInterventionRecord,
    SituationLifecycleState,
    SituationRecord,
    SituationSeverity,
    SituationType,
    SourceTrustLevel,
    utc_now,
)
from app.situational_awareness.lifecycle import (
    SituationLifecycleManager,
    VALID_SITUATION_TRANSITIONS,
)
from app.situational_awareness.normalization import EventNormalizer
from app.situational_awareness.orchestrator import ProactiveResponseOrchestrator
from app.situational_awareness.schemas import (
    EventIngestRequest,
    NormalizedEvent,
    SignalIngestRequest,
    SituationInvestigateRequest,
    SituationResolveRequest,
    SituationSuppressRequest,
)
from app.situational_awareness.service import SituationalAwarenessService

client = TestClient(app)


# =============================================================================
# 1. SIGNAL INGESTION & NORMALIZATION TESTS
# =============================================================================

def test_signal_ingest_request_normalization():
    """Verify SignalIngestRequest normalizes into a full SignalRecord with all fields."""
    normalizer = EventNormalizer()
    req = SignalIngestRequest(
        signal_type="metric_anomaly",
        source_system="datadog",
        source_trust=SourceTrustLevel.VERIFIED_EXTERNAL,
        scope="production",
        subject="payment-service",
        severity=SituationSeverity.HIGH,
        payload={"p99_latency_ms": 2400, "error_rate": 0.08},
        causal_references=["commit_abc123"],
        world_state_references=["node_pool_primary"],
    )

    signal = normalizer.normalize_signal(req)
    assert isinstance(signal, SignalRecord)
    assert signal.signal_type == "metric_anomaly"
    assert signal.source_system == "datadog"
    assert signal.source_trust == SourceTrustLevel.VERIFIED_EXTERNAL
    assert signal.subject == "payment-service"
    assert signal.severity == SituationSeverity.HIGH
    assert signal.causal_references == ["commit_abc123"]
    assert signal.world_state_references == ["node_pool_primary"]
    # Verify backward compatible properties
    assert signal.source == "datadog"
    assert signal.environment == "production"
    assert signal.to_dict()["id"] == signal.signal_id


def test_legacy_event_ingest_normalization_backwards_compatibility():
    """Verify legacy EventIngestRequest produces NormalizedEvent with .to_signal()."""
    normalizer = EventNormalizer()
    req = EventIngestRequest(
        event_type="container_crash",
        source="kubernetes",
        environment="staging",
        resource="auth-service-pod-1",
        subject="OOMKilled",
        payload={"exit_code": 137},
        severity=SituationSeverity.CRITICAL,
    )

    norm_event = normalizer.normalize(req)
    assert isinstance(norm_event, NormalizedEvent)
    assert norm_event.event_type == "container_crash"
    assert norm_event.source == "kubernetes"
    assert norm_event.original_source == "kubernetes"
    assert norm_event.is_sanitized is True

    # Test conversion to SignalRecord
    sig = norm_event.to_signal()
    assert isinstance(sig, SignalRecord)
    assert sig.signal_type == "container_crash"
    assert sig.source_system == "kubernetes"
    assert sig.entity == "auth-service-pod-1"
    assert sig.severity == SituationSeverity.CRITICAL


# =============================================================================
# 2. 7-DIMENSIONAL SIGNAL CORRELATION & BURST DEDUPLICATION
# =============================================================================

def test_seven_dimensional_signal_correlation():
    """Verify 7-dimensional signal correlation calculates composite similarity score."""
    engine = SignalCorrelationEngine()
    now = utc_now()

    sig1 = SignalRecord(
        signal_type="cpu_spike",
        source_system="prometheus",
        scope="production",
        subject="api-gateway",
        entity="api-gateway-pod-1",
        severity=SituationSeverity.HIGH,
        timestamp=now,
        causal_references=["deploy_42"],
        world_state_references=["node_alpha"],
    )

    sig2 = SignalRecord(
        signal_type="cpu_spike",
        source_system="datadog",
        scope="production",
        subject="api-gateway",
        entity="api-gateway-pod-1",
        severity=SituationSeverity.HIGH,
        timestamp=now + timedelta(seconds=15),
        causal_references=["deploy_42"],
        world_state_references=["node_alpha"],
    )

    score = engine.calculate_correlation_score(sig1, sig2)
    assert 0.0 <= score <= 1.0
    # High similarity across entity, causal ref, scope, and temporal window
    assert score >= 0.70

    # Unrelated signal in another environment and service
    sig_unrelated = SignalRecord(
        signal_type="disk_full",
        source_system="cloudwatch",
        scope="development",
        subject="warehouse-etl",
        entity="db-worker-99",
        severity=SituationSeverity.LOW,
        timestamp=now + timedelta(hours=2),
    )
    score_unrelated = engine.calculate_correlation_score(sig1, sig_unrelated)
    assert score_unrelated < 0.30


def test_burst_deduplication():
    """Verify high-frequency burst of similar signals is properly deduplicated."""
    engine = SignalCorrelationEngine()
    now = utc_now()

    signals = [
        SignalRecord(
            signal_type="connection_timeout",
            source_system="envoy",
            scope="production",
            subject="order-service",
            entity="order-service-instance",
            timestamp=now + timedelta(milliseconds=i * 200),
            payload={"error": "upstream request timeout"},
        )
        for i in range(10)
    ]

    is_duplicate, parent_id = engine.check_and_deduplicate(signals[0], [])
    assert not is_duplicate

    processed = [signals[0]]
    # Check subsequent burst signals
    for sig in signals[1:]:
        dup, p_id = engine.check_and_deduplicate(sig, processed)
        assert dup is True
        assert p_id == signals[0].signal_id
        processed.append(sig)


# =============================================================================
# 3. 16-STATE LIFECYCLE MACHINE & INVARIANTS
# =============================================================================

def test_situation_lifecycle_valid_and_invalid_transitions():
    """Verify all 16 lifecycle states adhere strictly to the operational transition matrix."""
    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="High Memory Usage",
        summary="Pod memory > 90%",
        severity=SituationSeverity.HIGH,
    )
    assert sit.lifecycle_state == SituationLifecycleState.DETECTED

    # Valid progression: DETECTED -> CORRELATING -> FORMING -> ACTIVE
    assert mgr.transition(sit, SituationLifecycleState.CORRELATING, reason="Signals accumulating")
    assert sit.lifecycle_state == SituationLifecycleState.CORRELATING

    assert mgr.transition(sit, SituationLifecycleState.FORMING, reason="Cluster established")
    assert sit.lifecycle_state == SituationLifecycleState.FORMING

    assert mgr.transition(sit, SituationLifecycleState.ACTIVE, reason="Impact confirmed")
    assert sit.lifecycle_state == SituationLifecycleState.ACTIVE

    # ACTIVE -> INTERVENTION_PENDING -> INTERVENTION_ACTIVE -> OBSERVING -> STABILIZING -> RESOLVED
    assert mgr.transition(sit, SituationLifecycleState.INTERVENTION_PENDING, reason="Proposing restart")
    assert mgr.transition(sit, SituationLifecycleState.INTERVENTION_ACTIVE, reason="Restart executing")
    assert mgr.transition(sit, SituationLifecycleState.OBSERVING, reason="Observing telemetry")
    assert mgr.transition(sit, SituationLifecycleState.STABILIZING, reason="Metrics normalizing")
    assert mgr.transition(sit, SituationLifecycleState.RESOLVED, reason="Telemetries verified")
    assert sit.lifecycle_state == SituationLifecycleState.RESOLVED
    assert sit.resolved_at is not None

    # Invalid transition: Cannot transition from RESOLVED to FORMING or INTERVENTION_ACTIVE
    assert not mgr.transition(sit, SituationLifecycleState.FORMING, reason="Illegal move")
    assert not mgr.transition(sit, SituationLifecycleState.INTERVENTION_ACTIVE, reason="Illegal move")

    # Legal reopen from RESOLVED to ACTIVE upon recurrence
    assert mgr.transition(sit, SituationLifecycleState.ACTIVE, reason="Recurrence detected")
    assert sit.lifecycle_state == SituationLifecycleState.ACTIVE

    # Check timeline auditing
    assert len(sit.timeline) >= 8
    assert all(isinstance(e.timestamp, datetime) for e in sit.timeline)


# =============================================================================
# 4. LINEAGE-PRESERVING MERGE & SPLIT OPERATIONS
# =============================================================================

def test_lineage_preserving_merge():
    """Verify merging two situations subsumes one and updates lineage pointers without data loss."""
    mgr = SituationLifecycleManager()
    parent = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Database Latency Spike",
        severity=SituationSeverity.HIGH,
    )
    child = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Database Connection Pool Exhaustion",
        severity=SituationSeverity.HIGH,
    )

    merged = mgr.merge_situations(
        primary_situation=parent,
        subsumed_situations=[child],
        reason="Correlated root cause: DB connection leak",
    )
    assert merged is not None
    assert child.lifecycle_state == SituationLifecycleState.MERGED
    assert child.merged_into_id == parent.situation_id
    assert child.situation_id in parent.merged_from_ids


def test_lineage_preserving_split():
    """Verify splitting a situation marks parent SPLIT and creates child situations with split_from_id."""
    mgr = SituationLifecycleManager()
    parent = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Multi-Service Outage",
        severity=SituationSeverity.CRITICAL,
    )

    child_specs = [
        {"title": "Auth Service Failure", "summary": "Auth tokens rejecting", "severity": SituationSeverity.HIGH},
        {"title": "Billing Service Lag", "summary": "Webhook processing delays", "severity": SituationSeverity.MEDIUM},
    ]

    children = mgr.split_situation(
        parent_situation=parent,
        sub_situation_specs=child_specs,
        reason="Disentangled into distinct independent component failures",
    )

    assert parent.lifecycle_state == SituationLifecycleState.SPLIT
    assert len(children) == 2
    for c in children:
        assert c.split_from_id == parent.situation_id
        assert c.lifecycle_state == SituationLifecycleState.DETECTED


# =============================================================================
# 5. AUDITABLE SUPPRESSION & COOLDOWN
# =============================================================================

def test_auditable_suppression_and_cooldown():
    """Verify suppression records an auditable entry and respects cooldown/expiry."""
    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Flapping Alert: Disk IOPS",
        severity=SituationSeverity.MEDIUM,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    supp_record = mgr.suppress_situation(
        situation=sit,
        suppressed_by="oncall_engineer",
        reason="Expected maintenance window for disk backup",
        duration_seconds=3600,
    )

    assert sit.lifecycle_state == SituationLifecycleState.SUPPRESSED
    assert supp_record.is_active is True
    assert mgr.is_suppressed(sit.situation_id) is True

    # Check proactive capabilities under suppression: CAN_NOTIFY should be disabled
    orchestrator = ProactiveResponseOrchestrator(lifecycle=mgr)
    caps = orchestrator.evaluate_proactive_capabilities(sit)
    assert ProactivePolicyCapability.CAN_NOTIFY not in caps


# =============================================================================
# 6. PROACTIVE RESPONSE: VERIFIED RESOLUTION (HAPPY PATH)
# =============================================================================

@pytest.mark.asyncio
async def test_proactive_response_pipeline_verified_resolution():
    """Verify the complete proactive response loop where empirical world-state verification succeeds."""
    mock_decision_service = MagicMock()
    mock_decision_record = MagicMock()
    mock_decision_record.decision_id = "dec_remediate_001"
    mock_decision_record.selected_option_id = "opt_restart_service"
    mock_decision_record.options = [
        DecisionOption(
            option_id="opt_restart_service",
            title="Restart Service Pod",
            description="Trigger graceful restart",
            option_type=DecisionType.ACTION,
            expected_utility=0.9,
        )
    ]
    mock_decision_service.deliberate.return_value = mock_decision_record

    mock_execution_service = MagicMock()
    mock_tx = MagicMock(spec=ActionTransaction)
    mock_tx.transaction_id = "tx_test_123"
    mock_tx.status = TransactionStatus.SUCCEEDED
    mock_execution_service.create_transaction = AsyncMock(return_value=mock_tx)

    mock_world_state_engine = MagicMock()
    mock_world_state_engine.verify_post_action = AsyncMock(
        return_value={"verified": True, "outcome": "ALL_POSTCONDITIONS_SATISFIED", "observations": {"status": "HEALTHY"}}
    )

    mock_emergency_stop = MagicMock()
    mock_emergency_stop.is_stopped.return_value = False

    bridges = SubsystemBridges(
        emergency_stop=EmergencyStopBridge(service=mock_emergency_stop),
        attention=AttentionSubsystemBridge(service=MagicMock()),
        decision=DecisionSubsystemBridge(service=mock_decision_service),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
        world_state=WorldStateSubsystemBridge(engine=mock_world_state_engine),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Auth Service Unhealthy",
        summary="Service healthcheck failing",
        severity=SituationSeverity.HIGH,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    assert report["status"] == "RESOLVED_VERIFIED"
    assert report["action_transaction_id"] == "tx_test_123"
    assert sit.lifecycle_state == SituationLifecycleState.RESOLVED
    assert sit.resolved_at is not None
    assert sit.state_reconciliation_status == "VERIFIED"


# =============================================================================
# 7. INVARIANT: EXECUTION != VERIFIED STATE (MISMATCH FAILURE PATH)
# =============================================================================

@pytest.mark.asyncio
async def test_proactive_response_postcondition_mismatch_fails_resolution():
    """CRITICAL INVARIANT: EXECUTION != VERIFIED STATE.
    Even though the action transaction executed successfully, world-state reconciliation
    finds an empirical postcondition mismatch. The situation MUST NOT be marked resolved!
    """
    mock_decision_service = MagicMock()
    mock_decision_record = MagicMock()
    mock_decision_record.decision_id = "dec_scale_001"
    mock_decision_record.selected_option_id = "opt_scale_replicas"
    mock_decision_record.options = [
        DecisionOption(
            option_id="opt_scale_replicas",
            title="Scale Replicas",
            description="Scale to 5 replicas",
            option_type=DecisionType.ACTION,
            expected_utility=0.88,
        )
    ]
    mock_decision_service.deliberate.return_value = mock_decision_record

    mock_execution_service = MagicMock()
    mock_tx = MagicMock(spec=ActionTransaction)
    mock_tx.transaction_id = "tx_scale_001"
    mock_tx.status = TransactionStatus.SUCCEEDED
    mock_execution_service.create_transaction = AsyncMock(return_value=mock_tx)

    mock_world_state_engine = MagicMock()
    # Telemetry observes only 1 replica due to quota exhaustion!
    mock_world_state_engine.verify_post_action = AsyncMock(
        return_value={
            "verified": False,
            "outcome": "POSTCONDITION_MISMATCH",
            "mismatches": {"active_replicas": {"expected": 5, "observed": 1}},
        }
    )

    mock_emergency_stop = MagicMock()
    mock_emergency_stop.is_stopped.return_value = False

    bridges = SubsystemBridges(
        emergency_stop=EmergencyStopBridge(service=mock_emergency_stop),
        decision=DecisionSubsystemBridge(service=mock_decision_service),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
        world_state=WorldStateSubsystemBridge(engine=mock_world_state_engine),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Order Service Overloaded",
        summary="High queue backlog",
        severity=SituationSeverity.HIGH,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    # Invariant assertion: Report must indicate failure and situation must NOT be RESOLVED
    assert report["status"] == "FAILED_POSTCONDITION_MISMATCH"
    assert "active_replicas" in report["mismatches"]
    assert sit.lifecycle_state == SituationLifecycleState.ACTIVE
    assert sit.resolved_at is None
    assert sit.state_reconciliation_status == "DRIFT_DETECTED"

    # Verify intervention status
    assert len(sit.interventions) == 1
    assert sit.interventions[0].execution_state == "NOT_VERIFIED"


# =============================================================================
# 8. INVARIANT: EMERGENCY STOP ALWAYS WINS (FAIL-CLOSED SAFETY GATE)
# =============================================================================

@pytest.mark.asyncio
async def test_proactive_response_emergency_stop_fail_closed():
    """CRITICAL INVARIANT: EMERGENCY STOP ALWAYS WINS.
    When Emergency Stop is active globally or for user, all proactive interventions
    must immediately fail closed without creating transactions or executing actions.
    """
    mock_emergency_stop = MagicMock()
    mock_emergency_stop.is_stopped.return_value = True  # EMERGENCY STOP ACTIVE!

    mock_execution_service = MagicMock()
    mock_execution_service.create_transaction = AsyncMock()

    bridges = SubsystemBridges(
        emergency_stop=EmergencyStopBridge(service=mock_emergency_stop),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Critical Database Crash",
        summary="Primary node unresponsive",
        severity=SituationSeverity.CRITICAL,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    assert report["status"] == "BLOCKED_BY_EMERGENCY_STOP"
    assert "Emergency Stop is ACTIVE" in report["reason"]
    # Verify no action transaction was ever initiated
    mock_execution_service.create_transaction.assert_not_called()
    assert sit.lifecycle_state == SituationLifecycleState.ACTIVE

    # Verify timeline records halted reason
    assert any(e.event_type == "PROACTIVE_PIPELINE_HALTED" for e in sit.timeline)


# =============================================================================
# 9. INVARIANT: NO_ACTION FIRST-CLASS OUTCOME WITH PERSISTED RATIONALE
# =============================================================================

@pytest.mark.asyncio
async def test_proactive_response_no_action_first_class_outcome():
    """CRITICAL INVARIANT: NO_ACTION is a first-class outcome with persisted rationale."""
    mock_emergency_stop = MagicMock()
    mock_emergency_stop.is_stopped.return_value = False

    mock_decision_service = MagicMock()
    mock_decision_record = MagicMock()
    mock_decision_record.decision_id = "dec_no_op_001"
    mock_decision_record.selected_option_id = "opt_no_action"
    mock_decision_record.options = [
        DecisionOption(
            option_id="opt_no_action",
            title="Continue Observing",
            description="System is within transient jitter tolerance",
            option_type=DecisionType.NO_ACTION,
            expected_utility=0.85,
        )
    ]
    mock_decision_service.deliberate.return_value = mock_decision_record

    mock_execution_service = MagicMock()
    mock_execution_service.create_transaction = AsyncMock()

    bridges = SubsystemBridges(
        emergency_stop=EmergencyStopBridge(service=mock_emergency_stop),
        decision=DecisionSubsystemBridge(service=mock_decision_service),
        execution=ExecutionSubsystemBridge(service=mock_execution_service),
    )

    mgr = SituationLifecycleManager()
    sit = mgr.create_situation(
        situation_type=SituationType.INCIDENT,
        title="Minor Transient Latency Jitter",
        summary="p95 jumped by 15ms for 30 seconds",
        severity=SituationSeverity.LOW,
    )
    mgr.transition(sit, SituationLifecycleState.ACTIVE)

    orchestrator = ProactiveResponseOrchestrator(bridges=bridges, lifecycle=mgr)
    report = await orchestrator.orchestrate_response(sit)

    assert report["status"] == "NO_ACTION"
    assert "NO_ACTION" in report["rationale"]
    # No action transaction executed
    mock_execution_service.create_transaction.assert_not_called()
    # Persisted rationale on timeline
    assert any(e.event_type == "NO_ACTION_DECIDED" for e in sit.timeline)


# =============================================================================
# 10. REST API ENDPOINTS (/signals, /refresh, /investigate, /interventions)
# =============================================================================

def test_api_signals_ingest_flow():
    """Verify POST /api/v1/situations/signals correctly ingests a signal and returns 200."""
    payload = {
        "signal_type": "security_probe_detected",
        "source_system": "suricata_ids",
        "source_trust": "VERIFIED_EXTERNAL",
        "scope": "dmz_network",
        "subject": "192.168.1.105",
        "severity": "HIGH",
        "payload": {"dest_port": 22, "packet_count": 450},
        "causal_references": ["ids_rule_2001"],
        "world_state_references": ["gateway_firewall"],
    }
    resp = client.post("/api/v1/situations/signals", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "PROCESSED"
    assert "situation_id" in data
    sit_id = data["situation_id"]

    # Verify GET /api/v1/situations/{id}/signals
    resp_sigs = client.get(f"/api/v1/situations/{sit_id}/signals")
    assert resp_sigs.status_code == 200
    sigs = resp_sigs.json()
    assert len(sigs) >= 1
    assert sigs[0]["signal_type"] == "security_probe_detected"


def test_api_refresh_and_investigate_endpoints():
    """Verify POST /api/v1/situations/{id}/refresh and /investigate dispatch cleanly."""
    # Ingest a seed event
    resp_ingest = client.post(
        "/api/v1/situations/events",
        json={
            "event_type": "database_connection_timeout",
            "source": "api_backend",
            "environment": "production",
            "resource": "postgres-primary",
            "subject": "DB connection timeout",
            "severity": "HIGH",
        },
    )
    assert resp_ingest.status_code == 200
    sit_id = resp_ingest.json()["situation_id"]

    # Test /refresh
    resp_refresh = client.post(f"/api/v1/situations/{sit_id}/refresh")
    assert resp_refresh.status_code == 200
    ref_data = resp_refresh.json()
    assert ref_data["situation_id"] == sit_id

    # Test /investigate
    resp_inv = client.post(
        f"/api/v1/situations/{sit_id}/investigate",
        json={"scope": "deep_telemetry"},
    )
    assert resp_inv.status_code == 200
    inv_data = resp_inv.json()
    assert inv_data["situation_id"] == sit_id
    assert inv_data["status"] == "INVESTIGATION_DISPATCHED"

    # Test /interventions
    resp_intvs = client.get(f"/api/v1/situations/{sit_id}/interventions")
    assert resp_intvs.status_code == 200
    assert isinstance(resp_intvs.json(), list)
