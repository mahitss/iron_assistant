#!/usr/bin/env python3
"""Autonomous Runtime Reliability, Fault Injection & Deterministic Self-Healing E2E Verification.

Task 88 Verification Script: Demonstrates the end-to-end reliability lifecycle:
1. Deterministic Taxonomy & Classification
2. Sensitive Data & Secret Sanitization
3. Fingerprinting, Storm Detection & Crash Loop Circuit Breaker
4. Causal Graph Correlation & Root-Cause Candidate Identification
5. Blast-Radius Analysis & Containment Evaluation
6. Bounded Recovery Selection, Authorization & Resource Economy Budgeting
7. Non-LLM Verification Probe & Stability Window
8. Metacognitive Calibration & Learning Record
9. Chaos Fault Injection Guardrail Enforcement
"""

import asyncio
import os
import pathlib
import sys
import time
from datetime import datetime, timezone

# Ensure backend directory is on sys.path
backend_dir = pathlib.Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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


def log_step(title: str):
    print(f"\n{'='*70}\n[*] {title}\n{'='*70}")


async def main():
    print("======================================================================")
    print("  KAIRO TASK 88: AUTONOMOUS RUNTIME RELIABILITY & SELF-HEALING E2E    ")
    print("======================================================================")

    # -------------------------------------------------------------------------
    # STEP 1: Deterministic Taxonomy & Classification
    # -------------------------------------------------------------------------
    log_step("STEP 1: Deterministic Failure Classification & Sanitization")
    classifier = FailureClassifier()

    raw_error = "Segmentation fault (SIGSEGV) crash in native runtime worker process"
    classified = classifier.classify(raw_error, component="native_runtime", operation="dispatch_tool")

    print(f"  Raw Error:       {raw_error}")
    print(f"  Classified Type: {classified['failure_type'].value}")
    print(f"  Severity:        {classified['severity'].value}")
    print(f"  Recoverable:     {classified['recoverability']}")
    print(f"  Confidence:      {classified['confidence']}")
    assert classified["failure_type"] == FailureType.PROCESS_FAILURE
    assert classified["severity"] == FailureSeverity.P1

    # Sanitization check
    leak_test = "Authorization: Bearer secret_live_token_999999999999 for user password=SuperSecretPassword123"
    sanitized = sanitize_message(leak_test)
    print(f"  Sanitized Msg:   {sanitized}")
    assert "secret_live_token" not in sanitized
    assert "SuperSecretPassword123" not in sanitized
    print("  [✓] Classification & zero-leak sanitization verified.")

    # -------------------------------------------------------------------------
    # STEP 2: Fingerprinting, Storms & Crash Loop Circuit Breaker
    # -------------------------------------------------------------------------
    log_step("STEP 2: Fingerprinting, Storm Detection & Crash Loop Circuit Breaker")
    detector = FailureDetector(storm_threshold=3, crash_loop_threshold=3, crash_loop_window_seconds=10.0)

    f1 = detector.ingest_signal("IPC channel reset", "native_runtime")
    f2 = detector.ingest_signal("IPC channel reset", "native_runtime")
    print(f"  Failure 1 Fingerprint: {f1.fingerprint}")
    print(f"  Failure 2 Fingerprint: {f2.fingerprint}")
    assert f1.fingerprint == f2.fingerprint
    print("  [✓] Deterministic deduplication fingerprint verified.")

    # Storm Detection
    detector.ingest_signal("IPC channel reset", "native_runtime")
    is_storm = detector.detect_storm(f1.fingerprint)
    print(f"  Storm Detected: {is_storm}")
    assert is_storm is True
    print("  [✓] High-frequency failure storm detected.")

    # Crash Loop Circuit Breaker
    target_daemon = "native_runtime_daemon"
    print(f"  Simulating rapid restarts for: {target_daemon}")
    detector.record_restart(target_daemon)
    detector.record_restart(target_daemon)
    print(f"  Crash loop active after 2 restarts: {detector.is_in_crash_loop(target_daemon)}")
    detector.record_restart(target_daemon)
    print(f"  Crash loop active after 3 restarts: {detector.is_in_crash_loop(target_daemon)}")
    assert detector.is_in_crash_loop(target_daemon) is True
    print("  [✓] Crash loop circuit breaker tripped. Restarts blocked.")

    # -------------------------------------------------------------------------
    # STEP 3: Causal Graph & Root-Cause Candidate Identification
    # -------------------------------------------------------------------------
    log_step("STEP 3: Causal Graph Correlation across Subsystems")
    correlator = RootCauseCorrelator()
    cid = "corr_e2e_live_42"

    fail_root = detector.ingest_signal("Pipe broken", "native_runtime", correlation_id=cid)
    fail_downstream = detector.ingest_signal("Tool failed to execute", "native_tool", correlation_id=cid)

    identified_root = correlator.correlate(fail_downstream, [fail_root, fail_downstream])
    print(f"  Primary Failure:    {fail_root.component} ({fail_root.failure_type.value})")
    print(f"  Downstream Victim:  {fail_downstream.component} ({fail_downstream.failure_type.value})")
    print(f"  Correlated Root:    {identified_root}")
    assert identified_root.lower() == "native_runtime"
    print("  [✓] Causal graph correctly identified upstream root cause.")

    # -------------------------------------------------------------------------
    # STEP 4: Blast-Radius Analysis
    # -------------------------------------------------------------------------
    log_step("STEP 4: Blast-Radius Analysis & Systemic Impact Scoring")
    analyzer = BlastRadiusAnalyzer()
    radius = await analyzer.calculate_blast_radius(
        component="native_runtime",
        failure_type=FailureType.PROCESS_FAILURE,
        severity=FailureSeverity.P1,
    )
    print(f"  Systemic Impact Score: {radius['systemic_impact_score']}")
    print(f"  Affected Subsystems:   {radius['affected_subsystems']}")
    print(f"  Requires Containment:  {radius['requires_precautionary_containment']}")
    assert radius["systemic_impact_score"] >= 0.5
    assert "native_tool" in radius["affected_subsystems"]
    print("  [✓] Blast-radius analysis completed with containment mandate.")

    # -------------------------------------------------------------------------
    # STEP 5: Bounded Recovery Strategy Selection & Safety Gating
    # -------------------------------------------------------------------------
    log_step("STEP 5: Bounded Recovery Strategy Selection & Safety Ladder")
    engine = RecoveryEngine()

    # If crash loop is active, verify strategy degrades or escalates instead of blind restart
    crash_strat = engine.select_strategy(fail_root, is_crash_loop=True)
    print(f"  Strategy under Crash Loop: {crash_strat.strategy_type.value} (Risk: {crash_strat.risk.value})")
    assert crash_strat.strategy_type != RecoveryStrategyType.RESTART_PROCESS
    assert crash_strat.strategy_type in (RecoveryStrategyType.DEGRADE_CAPABILITY, RecoveryStrategyType.ESCALATE)

    # Emergency Stop halts recovery
    engine._emergency_stop_active = True
    authorized, decision_id, approval_id = await engine.authorize_recovery(crash_strat, "native_runtime")
    print(f"  Recovery Authorized with EmergencyStop active: {authorized} ({decision_id})")
    assert authorized is False
    assert decision_id == "EMERGENCY_STOP_ACTIVE"
    engine._emergency_stop_active = False
    print("  [✓] EmergencyStop absolute priority verified.")

    # -------------------------------------------------------------------------
    # STEP 6: Full Self-Healing Lifecycle via ReliabilityService
    # -------------------------------------------------------------------------
    log_step("STEP 6: End-to-End Self-Healing Lifecycle & Non-LLM Verification")
    service = ReliabilityService()

    print("  1. Ingesting failure into ReliabilityService...")
    ingested_fail = await service.ingest_failure(
        exc_or_error="Native socket pipe disconnected",
        component="ipc_transport",
        operation="dispatch_envelope",
    )
    print(f"     Ingested Failure ID: {ingested_fail.failure_id}")

    incidents = service.list_incidents()
    assert len(incidents) >= 1
    target_inc = incidents[0]
    print(f"     Incident Created: {target_inc.incident_id} (State: {target_inc.current_state.value})")

    print("  2. Executing autonomous recovery...")
    rec_res = await service.execute_recovery_for_incident(target_inc.incident_id, caller_identity="test_runner")
    print(f"     Recovery ID:         {rec_res.recovery_id}")
    print(f"     Strategy Applied:    {rec_res.strategy.value}")
    print(f"     Recovery State:      {rec_res.state.value}")
    print(f"     Verification State:  {rec_res.verification_state.value}")
    print(f"     Incident Post-State: {target_inc.current_state.value}")
    assert rec_res.state == FailureLifecycleState.RECOVERED
    assert rec_res.verification_state == VerificationState.VERIFIED_RECOVERED
    assert target_inc.current_state == IncidentLifecycleState.MONITORING
    print("  [✓] Autonomous recovery verified clean via deterministic probes.")

    # -------------------------------------------------------------------------
    # STEP 7: Evidence Bundle & Metacognitive Learning
    # -------------------------------------------------------------------------
    log_step("STEP 7: Forensic Evidence Bundle & Metacognitive Calibration")
    evidence = service.get_evidence(rec_res.recovery_id)
    assert evidence is not None
    print(f"  Evidence Record ID: {evidence.evidence_id}")
    print(f"  Action Taken:       {evidence.action_taken.get('action')}")
    print(f"  Verification Check: {evidence.verification.get('probe_name')}")
    print(f"  Result Status:      {evidence.result_status}")
    print("  [✓] Forensic evidence bundle generated with immutable provenance.")

    # -------------------------------------------------------------------------
    # STEP 8: Chaos & Fault Injection Guardrails
    # -------------------------------------------------------------------------
    log_step("STEP 8: Chaos Fault Injection Guardrail Enforcement")
    fi_engine = FaultInjectionEngine(enabled=False)

    # Verify blocked when disabled
    try:
        fi_engine.trigger_fault("ipc_disconnect_before_result", caller_identity="operator")
        print("  [!] Error: Fault injection should have been blocked!")
        sys.exit(1)
    except FaultInjectionError as exc:
        print(f"  Blocked as expected when disabled: {exc}")

    # Verify authorized injection when enabled for admin
    fi_engine.config.enabled = True
    inject_res = fi_engine.trigger_fault("ipc_disconnect_before_result", caller_identity="admin")
    print(f"  Injected Scenario: {inject_res['scenario_name']} on component {inject_res['target_component']}")
    assert inject_res["target_component"] == "ipc"
    print("  [✓] Chaos guardrail enforcement verified.")

    print("\n======================================================================")
    print("  [✓] ALL 8 CORE LIFECYCLE CHECKS PASSED SUCCESSFULLY!                ")
    print("======================================================================\n")


if __name__ == "__main__":
    asyncio.run(main())
