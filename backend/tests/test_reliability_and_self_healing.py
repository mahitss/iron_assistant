"""Comprehensive unit and integration tests for Kairo Autonomous Runtime Reliability,

Fault Injection & Deterministic Self-Healing Engine (Task 88).
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import create_app
from app.reliability.blast_radius import BlastRadiusAnalyzer
from app.reliability.correlator import RootCauseCorrelator
from app.reliability.detector import FailureDetector
from app.reliability.fault_injection import FaultInjectionEngine, FaultInjectionError
from app.reliability.learning import ReliabilityLearner
from app.reliability.models import (
    FailureLifecycleState,
    IncidentLifecycleState,
    RecoveryStrategyType,
    SafeRecoveryClass,
    VerificationState,
)
from app.reliability.recovery_engine import RecoveryEngine
from app.reliability.service import ReliabilityService
from app.reliability.subsystems import SubsystemRecoveryAdapter
from app.reliability.taxonomy import (
    FailureClassifier,
    FailureSeverity,
    FailureType,
    sanitize_message,
    sanitize_payload,
)
from app.reliability.verifier import RecoveryVerifier


# ==============================================================================
# 1. DETERMINISTIC TAXONOMY, CLASSIFICATION & SANITIZATION
# ==============================================================================

def test_failure_classification_and_severity():
    """Verify deterministic mapping of raw exceptions to classified FailureType and Severity."""
    classifier = FailureClassifier()

    # Native crash
    d1 = classifier.classify("Fatal signal 11 SEGV received in native runtime worker", "native_runtime")
    assert d1["failure_type"] == FailureType.PROCESS_FAILURE
    assert d1["severity"] == FailureSeverity.P1

    # Broken pipe / IPC disconnect
    d2 = classifier.classify(BrokenPipeError("Pipe disconnected unexpectedly"), "ipc_transport")
    assert d2["failure_type"] == FailureType.IPC_FAILURE
    assert d2["severity"] == FailureSeverity.P2

    # Deadline exceeded
    d3 = classifier.classify(asyncio.TimeoutError("Execution deadline exceeded"), "tool_runner")
    assert d3["failure_type"] == FailureType.TIMEOUT
    assert d3["severity"] == FailureSeverity.P3

    # Memory limit
    d4 = classifier.classify("Out of memory: memory limit reached for cgroup", "sandbox")
    assert d4["failure_type"] == FailureType.MEMORY_PRESSURE
    assert d4["severity"] == FailureSeverity.P1

    # Fallback to unknown / unclassified failure
    d5 = classifier.classify(KeyError("missing_field"), "data_pipeline")
    assert d5["failure_type"] == FailureType.UNKNOWN_FAILURE
    assert d5["severity"] == FailureSeverity.P2


def test_sensitive_data_sanitization():
    """Verify passwords, authorization bearer tokens, and hashes are redacted."""
    raw_msg = (
        "Failed request to https://api.internal/v1 with Authorization: Bearer secret_token_abc_12345 "
        "and password=MySecretP@ssword! from ip 192.168.1.50"
    )
    sanitized = sanitize_message(raw_msg)
    assert "secret_token_abc_12345" not in sanitized
    assert "Bearer [REDACTED_TOKEN]" in sanitized
    assert "MySecretP@ssword!" not in sanitized
    assert "[REDACTED]" in sanitized

    raw_payload = {
        "user": "alice",
        "api_key": "sk-1234567890abcdef1234567890abcdef",
        "auth_token": "jwt.header.payload.sig",
        "nested": {"client_secret": "super_secret_val"},
    }
    sanitized_dict = sanitize_payload(raw_payload)
    assert sanitized_dict["api_key"] == "[REDACTED]"
    assert sanitized_dict["auth_token"] == "[REDACTED]"
    assert sanitized_dict["nested"]["client_secret"] == "[REDACTED]"
    assert sanitized_dict["user"] == "alice"


# ==============================================================================
# 2. DETERMINISTIC FINGERPRINTING, STORMS & CRASH LOOPS
# ==============================================================================

def test_deterministic_fingerprint_and_storm_detection():
    """Verify identical errors produce matching fingerprints and high frequencies detect storms."""
    detector = FailureDetector(storm_threshold=4, storm_window_seconds=10.0)

    f1 = detector.ingest_signal("Database connection dropped", "postgres_adapter")
    f2 = detector.ingest_signal("Database connection dropped", "postgres_adapter")
    assert f1.fingerprint == f2.fingerprint

    # Emit multiple to trigger storm
    assert not detector.detect_storm(f1.fingerprint)
    detector.ingest_signal("Database connection dropped", "postgres_adapter")
    detector.ingest_signal("Database connection dropped", "postgres_adapter")
    assert detector.detect_storm(f1.fingerprint) is True


def test_crash_loop_circuit_breaker():
    """Verify rapid repeated restarts trigger crash-loop detection and circuit breaking."""
    detector = FailureDetector(crash_loop_threshold=3, crash_loop_window_seconds=30.0)
    comp = "native_runtime_daemon"

    assert not detector.is_in_crash_loop(comp)
    detector.record_restart(comp)
    detector.record_restart(comp)
    assert not detector.is_in_crash_loop(comp)

    # 3rd restart inside window trips circuit breaker
    detector.record_restart(comp)
    assert detector.is_in_crash_loop(comp) is True

    # Clearing resets breaker
    detector.clear_crash_loop(comp)
    assert not detector.is_in_crash_loop(comp)


# ==============================================================================
# 3. ROOT CAUSE CORRELATION & CAUSAL GRAPH
# ==============================================================================

def test_root_cause_correlation_across_subsystems():
    """Verify correlator maps downstream failures to the primary dependency failure."""
    detector = FailureDetector()
    correlator = RootCauseCorrelator()
    cid = "corr_e2e_test_123"

    # 1. Primary failure in native_runtime
    fail_root = detector.ingest_signal("Pipe broken", "native_runtime", correlation_id=cid)
    # 2. Downstream failure in native_tool
    fail_downstream = detector.ingest_signal("Tool failed to execute", "native_tool", correlation_id=cid)

    root_cause = correlator.correlate(fail_downstream, [fail_root, fail_downstream])
    assert root_cause.lower() == "native_runtime"


# ==============================================================================
# 4. BLAST-RADIUS ANALYSIS
# ==============================================================================

@pytest.mark.asyncio
async def test_blast_radius_calculation():
    """Verify systemic impact scoring and downstream affected subsystems calculation."""
    analyzer = BlastRadiusAnalyzer()

    # Impact of native_runtime failure
    radius = await analyzer.calculate_blast_radius(
        component="native_runtime",
        failure_type=FailureType.PROCESS_FAILURE,
        severity=FailureSeverity.P1,
    )
    assert radius["systemic_impact_score"] >= 0.5
    assert "native_tool" in radius["affected_subsystems"]
    assert "computer" in radius["affected_subsystems"]
    assert radius["severity"] == "P1"
    assert radius["requires_precautionary_containment"] is True


# ==============================================================================
# 5. BOUNDED RECOVERY STRATEGY SELECTION & SAFETY CLASSES
# ==============================================================================

def test_recovery_strategy_selection_ladder():
    """Verify strategy escalation ladder from retry to restart to degradation."""
    engine = RecoveryEngine()
    detector = FailureDetector()

    comp = "cache_layer"
    fail = detector.ingest_signal(ConnectionResetError("Socket reset"), comp)

    # 1. First attempt -> RETRY or RECONNECT
    s1 = engine.select_strategy(fail, is_crash_loop=False)
    assert s1.strategy_type in (RecoveryStrategyType.RETRY, RecoveryStrategyType.RECONNECT)
    engine.record_attempt(comp, s1.strategy_type)

    # 2. If crash loop active -> strategy automatically avoids blind restarts
    s_crash = engine.select_strategy(fail, is_crash_loop=True)
    assert s_crash.strategy_type != RecoveryStrategyType.RESTART_PROCESS
    assert s_crash.strategy_type in (RecoveryStrategyType.DEGRADE_CAPABILITY, RecoveryStrategyType.ESCALATE)


# ==============================================================================
# 6. GOVERNANCE, APPROVAL & EMERGENCY STOP GATING
# ==============================================================================

@pytest.mark.asyncio
async def test_emergency_stop_halts_recovery():
    """Verify active EmergencyStop blocks recovery unconditionally."""
    engine = RecoveryEngine()
    detector = FailureDetector()

    fail = detector.ingest_signal("Daemon killed", "native_runtime")
    strategy = engine.select_strategy(fail)

    # Simulate emergency stop active
    engine._emergency_stop_active = True
    authorized, decision_id, approval_id = await engine.authorize_recovery(strategy, "native_runtime")
    assert authorized is False
    assert decision_id == "EMERGENCY_STOP_ACTIVE"


# ==============================================================================
# 7. RESOURCE BUDGET RESERVATION FOR RECOVERY
# ==============================================================================

@pytest.mark.asyncio
async def test_recovery_resource_budget_lifecycle():
    """Verify recovery reserves budget prior to execution and releases afterwards."""
    engine = RecoveryEngine()
    detector = FailureDetector()

    fail = detector.ingest_signal("Process stalled", "sandbox")
    strategy = engine.select_strategy(fail)

    task_id = "recovery_test_task_1"
    ok, reservation_id = await engine.reserve_recovery_budget(strategy, task_id)
    assert ok is True
    assert reservation_id.startswith("rsv_rec_")

    # Release reservation
    await engine.release_recovery_budget(reservation_id, task_id)


# ==============================================================================
# 8. DETERMINISTIC NON-LLM VERIFICATION & STABILITY MONITORING
# ==============================================================================

@pytest.mark.asyncio
async def test_deterministic_non_llm_verification():
    """Verify recovery actions are validated through synthetic probes, not LLM checks."""
    verifier = RecoveryVerifier(stability_window_seconds=1.0)
    adapter = SubsystemRecoveryAdapter()

    # Execute recovery action on memory cache
    res = await adapter.execute_recovery_action("memory_cache", RecoveryStrategyType.RELEASE_LEAKED_RESOURCE)
    v_res = await verifier.verify_recovery("memory_cache", RecoveryStrategyType.RELEASE_LEAKED_RESOURCE, res)

    assert v_res.state == VerificationState.VERIFIED_RECOVERED
    assert v_res.probe_name == "action_telemetry_check"
    assert v_res.passed is True


# ==============================================================================
# 9. END-TO-END AUTONOMOUS SELF-HEALING LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_service_ingest_recovery_and_learning_lifecycle():
    """Verify complete self-healing pipeline: ingest -> classify -> correlate -> assess -> recover -> verify -> learn."""
    service = ReliabilityService()

    # 1. Ingest failure
    fail = await service.ingest_failure(
        exc_or_error="IPC channel broke",
        component="ipc_transport",
        operation="dispatch_envelope",
    )
    assert fail.state in (FailureLifecycleState.ASSESSING, FailureLifecycleState.CORRELATED)
    incidents = service.list_incidents()
    assert len(incidents) == 1
    inc = incidents[0]
    assert inc.root_cause_candidate.lower() == "ipc_transport"

    # 2. Execute recovery
    rec = await service.execute_recovery_for_incident(inc.incident_id, caller_identity="test_runner")
    assert rec.state == FailureLifecycleState.RECOVERED
    assert rec.verification_state == VerificationState.VERIFIED_RECOVERED

    # 3. Check incident transitioned to MONITORING stability window
    assert inc.current_state == IncidentLifecycleState.MONITORING

    # 4. Check evidence bundle created
    evi = service.get_evidence(rec.recovery_id)
    assert evi is not None
    assert evi.strategy == rec.strategy.value
    assert evi.result_status == FailureLifecycleState.RECOVERED.value


# ==============================================================================
# 10. FAULT INJECTION GUARDRAILS
# ==============================================================================

def test_fault_injection_guardrail_blocking():
    """Verify fault injection engine cannot trigger faults when disabled."""
    engine = FaultInjectionEngine(enabled=False)
    with pytest.raises(FaultInjectionError, match="Fault injection is disabled"):
        engine.trigger_fault("ipc_disconnect_before_result", "operator")

    # When enabled with valid token
    engine.config.enabled = True
    res = engine.trigger_fault("ipc_disconnect_before_result", "admin")
    assert res["scenario_name"] == "ipc_disconnect_before_result"
    assert res["target_component"] == "ipc"


# ==============================================================================
# 11. REST API ROUTER INTEGRATION
# ==============================================================================

@pytest.mark.asyncio
async def test_reliability_rest_api_endpoints():
    """Verify HTTP API contracts for health, incidents, failures, and recovery."""
    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health endpoint
        h_resp = await client.get("/api/v1/reliability/health")
        assert h_resp.status_code == 200
        health = h_resp.json()
        assert "status" in health
        assert "open_incidents_count" in health
        assert "crash_loops_active" in health

        # 2. Incidents endpoint
        inc_resp = await client.get("/api/v1/reliability/incidents")
        assert inc_resp.status_code == 200
        assert isinstance(inc_resp.json(), list)

        # 3. Failures endpoint
        f_resp = await client.get("/api/v1/reliability/failures")
        assert f_resp.status_code == 200
        assert isinstance(f_resp.json(), list)

        # 4. Recovery list endpoint
        r_resp = await client.get("/api/v1/reliability/recovery")
        assert r_resp.status_code == 200
        assert isinstance(r_resp.json(), list)

        # 5. Components dependency matrix
        c_resp = await client.get("/api/v1/reliability/components")
        assert c_resp.status_code == 200
        comp_data = c_resp.json()
        assert "dependencies" in comp_data
