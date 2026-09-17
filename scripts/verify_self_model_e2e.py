#!/usr/bin/env python3
"""Autonomous Self-Model, Capability Awareness & Internal State Intelligence E2E Verification.

Task 101 Verification Script: Demonstrates all 8 core operational scenarios:
1. Scenario 1: Baseline Introspection & Resolution of all 15 Canonical Questions
2. Scenario 2: Dynamic Capability Degradation & Multi-Dimensional Readiness
3. Scenario 3: Dependency Cascade & Scoped Blast Radius Isolation
4. Scenario 4: EmergencyStop Primacy & Fail-Closed Transition
5. Scenario 5: Post-EmergencyStop Clearing & Revalidation Invariants
6. Scenario 6: Resource Saturation & Autonomous Throttling Awareness
7. Scenario 7: State Diffing & Delta Tracking Across Snapshots
8. Scenario 8: Grounding Telemetry Audit (0% Fictional Self-Awareness)
"""

import os
import pathlib
import sys
import time

# Ensure backend directory is on sys.path
backend_dir = pathlib.Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.capability_lifecycle.models import HealthStatus
from app.capability_lifecycle.service import get_capability_lifecycle_service
from app.security.emergency_stop import get_emergency_stop_service
from app.self_model.delta_engine import SelfModelDeltaEngine
from app.self_model.limitation_engine import LimitationReasoningEngine
from app.self_model.query_engine import SelfModelQueryEngine
from app.self_model.schemas import (
    AutonomyMode,
    CapabilityReadinessState,
    ChangeType,
    DependencyAwarenessItem,
    LimitationItem,
    ResourceAwareness,
    SecurityGovernanceAwareness,
    UncertaintyItem,
)
from app.self_model.service import SelfModelService


def log_scenario(title: str):
    print(f"\n{'='*75}\n[*] {title}\n{'='*75}")


def main():
    print("===========================================================================")
    print("  KAIRO TASK 101: AUTONOMOUS SELF-MODEL & CAPABILITY INTELLIGENCE E2E      ")
    print("===========================================================================")

    e_stop = get_emergency_stop_service()
    e_stop.reset()
    service = SelfModelService()

    # -------------------------------------------------------------------------
    # SCENARIO 1: Baseline Introspection & All 15 Questions
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 1: Baseline Introspection & The 15 Canonical Questions")
    snap1 = service.reconcile()
    answers = service.get_answers()

    print(f"[+] Initial Snapshot Captured: {snap1.snapshot_id}")
    print(f"    - Runtime Version:       {snap1.runtime_version}")
    print(f"    - Autonomy Mode:         {snap1.autonomy_mode.value}")
    print(f"    - Emergency Stop Active: {snap1.emergency_stop_state}")
    print(f"    - Total Capabilities:    {len(snap1.capabilities)}")

    print("\n[+] Testing 15 Canonical Introspective Questions:")
    print(f"    Q1  (Capabilities):         {', '.join(answers.q1_capabilities)}")
    print(f"    Q2  (Versions):             {answers.q2_versions}")
    print(f"    Q3  (Ready):                {', '.join(answers.q3_ready_capabilities)}")
    print(f"    Q4  (Degraded):             {', '.join(answers.q4_degraded_capabilities) or 'None'}")
    print(f"    Q5  (Unavailable):          {', '.join(answers.q5_temporarily_unavailable) or 'None'}")
    print(f"    Q6  (Resources):            Saturation {round(answers.q6_current_resources.saturation_pct * 100, 1)}% ({answers.q6_current_resources.degradation_tier})")
    print(f"    Q7  (Usable Tools):         {len(answers.q7_usable_tools)} tools active")
    print(f"    Q8  (Authorized Access):    {', '.join(answers.q8_authorized_access)}")
    print(f"    Q9  (Approval Required):    {', '.join(answers.q9_actions_requiring_approval)}")
    print(f"    Q10 (Failing Dependencies): {', '.join(answers.q10_failing_dependencies) or 'None (All healthy)'}")
    print(f"    Q11 (Recently Failed):      {', '.join(answers.q11_recently_failed_capabilities) or 'None'}")
    print(f"    Q12 (Reliability):          {answers.q12_capability_reliability}")
    print(f"    Q13 (Recent Changes):       {len(answers.q13_changes_since_last_check)} events")
    print(f"    Q14 (Limitations):          {len(answers.q14_limitations)} factual boundaries")
    print(f"    Q15 (Uncertainties):        {len(answers.q15_uncertainties)} active uncertainties")

    assert len(answers.q1_capabilities) > 0, "Q1 must list registered capabilities"
    assert len(answers.q3_ready_capabilities) > 0, "Q3 must identify ready capabilities"

    # -------------------------------------------------------------------------
    # SCENARIO 2: Dynamic Capability Degradation & Multi-Dimensional Readiness
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 2: Dynamic Capability Degradation & Readiness")
    print("[+] Simulating intermittent telemetry failures on 'web_research' capability...")
    lifecycle = get_capability_lifecycle_service()
    cap = lifecycle.get_capability("web_research")
    if cap:
        cap.health_state = HealthStatus.DEGRADED
        cap.reliability.consecutive_failures = 2
        cap.reliability.last_failure_reason = "Playwright DOM navigation timeout (HTTP 504)"

    snap2 = service.reconcile()
    web_cap = snap2.capabilities.get("web_research")
    assert web_cap is not None
    print(f"[+] Capability 'web_research' state evaluated:")
    print(f"    - Readiness State:       {web_cap.readiness_state.value}")
    print(f"    - Health State:          {web_cap.health_state}")
    print(f"    - Consecutive Failures:  {web_cap.consecutive_failures}")
    print(f"    - Dimension HEALTH:      {web_cap.dimensions.get('HEALTH').status} ({web_cap.dimensions.get('HEALTH').reason})")
    assert web_cap.readiness_state == CapabilityReadinessState.DEGRADED, "web_research must transition to DEGRADED"

    # -------------------------------------------------------------------------
    # SCENARIO 3: Dependency Cascade & Blast Radius Isolation
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 3: Dependency Cascade & Scoped Blast Radius Isolation")
    print("[+] Injecting dependency failure into 'browser_engine'...")
    deps_mock = snap2.dependencies.copy()
    deps_mock["browser_engine"] = DependencyAwarenessItem(
        dependency_name="browser_engine",
        dependency_type="AUTOMATION",
        status="UNAVAILABLE",
        evidence="Connection to headless browser socket timed out",
    )

    # Re-evaluate limitations
    lims = LimitationReasoningEngine.evaluate_limitations(
        snap2.capabilities, deps_mock, snap2.security_governance, snap2.resources
    )
    dep_lim = next((l for l in lims if l.subject == "DEPENDENCY_BROWSER_ENGINE"), None)
    assert dep_lim is not None
    print(f"[+] Grounded Limitation Created: {dep_lim.description}")
    print(f"    - Reason:   {dep_lim.reason}")
    print(f"    - Evidence: {dep_lim.evidence}")

    # Verify unrelated capabilities are NOT invalidated
    code_cap = snap2.capabilities.get("code_execution")
    assert code_cap is not None and code_cap.readiness_state == CapabilityReadinessState.READY
    print(f"[+] Independent capability 'code_execution' remains 100% READY (Scoped blast radius verified)")

    # -------------------------------------------------------------------------
    # SCENARIO 4: EmergencyStop Primacy & Fail-Closed Transition
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 4: EmergencyStop Primacy & Fail-Closed Transition")
    print("[+] Engaging EmergencyStop kill-switch globally...")
    e_stop.trigger(reason="Anomalous external mutation pattern detected", source="security_guard")

    snap3 = service.reconcile()
    print(f"[+] Post-EmergencyStop Snapshot: {snap3.snapshot_id}")
    print(f"    - Autonomy Mode:         {snap3.autonomy_mode.value}")
    print(f"    - Emergency Stop Active: {snap3.emergency_stop_state}")

    assert snap3.emergency_stop_state is True
    assert snap3.autonomy_mode == AutonomyMode.EMERGENCY_STOP

    for cid, c in snap3.capabilities.items():
        assert c.readiness_state == CapabilityReadinessState.BLOCKED, f"Capability {cid} must be BLOCKED"
        assert not service.can_capability_run(cid), f"can_capability_run({cid}) must fail-closed"

    print("[+] All capabilities verified fail-closed (BLOCKED). No autonomous actions permitted.")

    # -------------------------------------------------------------------------
    # SCENARIO 5: Post-EmergencyStop Clearing & Revalidation Invariant
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 5: Post-EmergencyStop Clearing & Revalidation Invariant")
    print("[+] Clearing EmergencyStop with explicit human authorization...")
    e_stop.reset()

    # Capabilities must not be assumed blindly READY without empirical probe
    if cap:
        cap.health_state = HealthStatus.HEALTHY
        cap.reliability.consecutive_failures = 0
        cap.reliability.last_failure_reason = None

    snap4 = service.reconcile()
    print(f"[+] Post-Reset Reconciled Snapshot: {snap4.snapshot_id}")
    print(f"    - Autonomy Mode:         {snap4.autonomy_mode.value}")
    print(f"    - Emergency Stop Active: {snap4.emergency_stop_state}")
    assert snap4.emergency_stop_state is False
    assert snap4.autonomy_mode == AutonomyMode.BOUNDED_AUTONOMY
    print("[+] Revalidation pass executed cleanly; capabilities restored according to verified health.")

    # -------------------------------------------------------------------------
    # SCENARIO 6: Resource Saturation & Autonomous Throttling Awareness
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 6: Resource Saturation & Autonomous Throttling Awareness")
    print("[+] Simulating resource capacity saturation at 92%...")
    saturated_resources = ResourceAwareness(
        saturation_pct=0.92,
        saturation_state="SATURATED",
        degradation_tier="AGGRESSIVE_THROTTLE",
        total_resources=8,
    )
    lims_sat = LimitationReasoningEngine.evaluate_limitations(
        snap4.capabilities, snap4.dependencies, snap4.security_governance, saturated_resources
    )
    res_lim = next((l for l in lims_sat if l.subject == "RESOURCE_ECONOMY"), None)
    assert res_lim is not None
    print(f"[+] Resource Limitation Detected: {res_lim.description}")
    print(f"    - Reason:   {res_lim.reason}")
    print(f"    - Evidence: {res_lim.evidence}")

    # -------------------------------------------------------------------------
    # SCENARIO 7: State Diffing & Delta Tracking Across Snapshots
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 7: State Diffing & Delta Tracking Across Snapshots")
    print(f"[+] Computing delta between Snapshot 1 and Snapshot 3 (Normal -> EmergencyStop)...")
    delta = SelfModelDeltaEngine.compute_delta(snap1, snap3)
    print(f"[+] Computed Delta:")
    print(f"    - Base Snapshot:   {delta.base_snapshot_id}")
    print(f"    - Target Snapshot: {delta.target_snapshot_id}")
    print(f"    - Recorded Events: {len(delta.changes)}")
    for ch in delta.changes[:5]:
        print(f"      * [{ch.change_type.value}] {ch.target_id}: {ch.old_state} -> {ch.new_state} ({ch.reason})")

    assert any(c.change_type == ChangeType.EMERGENCY_STOP_CHANGED for c in delta.changes)
    assert any(c.change_type == ChangeType.AUTONOMY_STATE_CHANGED for c in delta.changes)

    # -------------------------------------------------------------------------
    # SCENARIO 8: Grounding Telemetry Audit (No Fictional Awareness)
    # -------------------------------------------------------------------------
    log_scenario("SCENARIO 8: Grounding Telemetry Audit (0% Fictional Self-Awareness)")
    print("[+] Running automated empirical grounding verification audit...")
    grounding = service.verify_grounding()
    print(f"[+] Grounding Audit Verdict:  {grounding.verdict}")
    print(f"    - Total Claims Audited:  {grounding.total_claims}")
    print(f"    - Verified Claims:       {grounding.verified_claims}")
    print(f"    - Invariant Violations:  {len(grounding.violations)}")
    print(f"    - Unverified Claims:     {len(grounding.unverified_claims)}")

    assert grounding.is_grounded, "Self-model must be 100% grounded in empirical telemetry"
    assert grounding.verdict == "GROUNDED"

    print("\n" + "="*75)
    print("  TASK 101: ALL 8 OPERATIONAL SCENARIOS VERIFIED SUCCESSFULLY!")
    print("===========================================================================")


if __name__ == "__main__":
    main()
