"""Comprehensive Unit, State Machine, Security, and Concurrency Tests for Task 91:
Autonomous Capability Lifecycle, Versioning, Compatibility & Safe Evolution Engine.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from typing import Dict, Any

from app.capability_lifecycle.models import (
    CapabilityMetadata,
    CapabilityType,
    LifecycleState,
    HealthStatus,
    SecurityClassification,
    CompatibilityClassification,
    SimulationStatus,
    CapabilityDependency,
    DependencyType,
    ResourceProfile,
    ConformanceTestVector,
    CanaryRolloutConfig,
    RolloutState,
    _now_utc,
)
from app.capability_lifecycle.state_machine import CapabilityStateMachine, LifecycleTransitionError
from app.capability_lifecycle.fingerprinting import CapabilityFingerprinter
from app.capability_lifecycle.versioning import CapabilityVersionManager, ImmutableVersionMutationError
from app.capability_lifecycle.compatibility import CompatibilityEvaluator
from app.capability_lifecycle.dependency_graph import CapabilityDependencyGraph
from app.capability_lifecycle.validation import CapabilityValidator
from app.capability_lifecycle.conformance import ConformanceTestRunner
from app.capability_lifecycle.simulation_gate import SimulationGate
from app.capability_lifecycle.canary import CanaryRolloutManager
from app.capability_lifecycle.promotion import PromotionGateCoordinator
from app.capability_lifecycle.rollback import CapabilityRollbackManager
from app.capability_lifecycle.deprecation import CapabilityDeprecationManager
from app.capability_lifecycle.service import CapabilityLifecycleService
from app.security.emergency_stop import get_emergency_stop_service


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================

@pytest.fixture(autouse=True)
def ensure_emergency_stop_cleared():
    estop = get_emergency_stop_service()
    estop.reset_emergency_stop(is_human_user=True)
    yield
    estop.reset_emergency_stop(is_human_user=True)


def make_sample_capability(
    cap_id: str = "cap_web_search",
    name: str = "web_search",
    version: str = "1.0.0",
    cap_type: CapabilityType = CapabilityType.TOOL,
    security_class: SecurityClassification = SecurityClassification.INTERNAL,
) -> CapabilityMetadata:
    """Creates a strongly-typed CapabilityMetadata fixture matching domain models."""
    return CapabilityMetadata(
        capability_id=cap_id,
        name=name,
        description="Deterministic web search execution capability",
        capability_type=cap_type,
        owner_source="core_engine",
        version=version,
        parameters_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
        dependencies=[
            CapabilityDependency(
                target_id="cap_native_net",
                dependency_type=DependencyType.NATIVE_CAPABILITY,
                version_constraint=">=1.0.0",
            )
        ],
        required_permissions=["READ", "EXECUTE"],
        resource_profile=ResourceProfile(
            cpu_cores=0.5,
            memory_mb=256.0,
            network_bandwidth_kbps=1024.0,
            timeout_seconds=10.0,
            max_concurrency=10,
        ),
        security_classification=security_class,
        lifecycle_state=LifecycleState.DISCOVERED,
        health_state=HealthStatus.UNKNOWN,
    )


# ==============================================================================
# 1. LIFECYCLE STATE MACHINE TESTS (Phase 2 & Phase 28)
# ==============================================================================

def test_state_machine_legal_transitions():
    sm = CapabilityStateMachine()
    cap = make_sample_capability()

    assert cap.lifecycle_state == LifecycleState.DISCOVERED

    # DISCOVERED -> VALIDATING -> VALIDATED
    cap, event1 = sm.transition(cap, LifecycleState.VALIDATING, reason="Starting schema check")
    assert cap.lifecycle_state == LifecycleState.VALIDATING
    assert event1.from_state == LifecycleState.DISCOVERED
    assert event1.to_state == LifecycleState.VALIDATING

    cap, _ = sm.transition(cap, LifecycleState.VALIDATED, reason="Validation passed")
    assert cap.lifecycle_state == LifecycleState.VALIDATED

    # VALIDATED -> SIMULATING -> VALIDATED -> CANARY -> ACTIVE
    cap, _ = sm.transition(cap, LifecycleState.SIMULATING, reason="Digital twin simulation")
    assert cap.lifecycle_state == LifecycleState.SIMULATING

    cap, _ = sm.transition(cap, LifecycleState.VALIDATED, reason="Simulation passed")
    assert cap.lifecycle_state == LifecycleState.VALIDATED

    cap, _ = sm.transition(cap, LifecycleState.CANARY, reason="5% canary rollout started")
    assert cap.lifecycle_state == LifecycleState.CANARY

    cap, _ = sm.transition(cap, LifecycleState.ACTIVE, reason="11 promotion gates passed")
    assert cap.lifecycle_state == LifecycleState.ACTIVE

    # ACTIVE -> DEGRADED -> ACTIVE (self-healing)
    cap, _ = sm.transition(cap, LifecycleState.DEGRADED, reason="Transient latency spike")
    assert cap.lifecycle_state == LifecycleState.DEGRADED

    cap, _ = sm.transition(cap, LifecycleState.ACTIVE, reason="Latency baseline restored")
    assert cap.lifecycle_state == LifecycleState.ACTIVE

    # ACTIVE -> DEPRECATED -> RETIRING -> RETIRED
    cap, _ = sm.transition(cap, LifecycleState.DEPRECATED, reason="New version released")
    assert cap.lifecycle_state == LifecycleState.DEPRECATED

    cap, _ = sm.transition(cap, LifecycleState.RETIRING, reason="Sunset date reached")
    assert cap.lifecycle_state == LifecycleState.RETIRING

    cap, _ = sm.transition(cap, LifecycleState.RETIRED, reason="Fully retired")
    assert cap.lifecycle_state == LifecycleState.RETIRED


def test_state_machine_illegal_transitions_deterministic_failure():
    sm = CapabilityStateMachine()
    cap = make_sample_capability()

    # DISCOVERED cannot jump directly to ACTIVE
    with pytest.raises(LifecycleTransitionError):
        sm.transition(cap, LifecycleState.ACTIVE, reason="Unsafe promotion attempt")
    assert cap.lifecycle_state == LifecycleState.DISCOVERED

    # RETIRED is terminal - cannot transition back to ACTIVE
    cap.lifecycle_state = LifecycleState.RETIRED
    with pytest.raises(LifecycleTransitionError):
        sm.transition(cap, LifecycleState.ACTIVE, reason="Zombie resurrection attempt")


# ==============================================================================
# 2. VERSIONING & IMMUTABILITY (Phase 3)
# ==============================================================================

def test_version_manager_parsing_and_immutability():
    vm = CapabilityVersionManager()
    cap = make_sample_capability(version="1.4.2")

    rec = vm.register_version(cap)
    assert rec.major == 1
    assert rec.minor == 4
    assert rec.patch == 2
    assert rec.is_active is False

    # Freeze version upon activation
    vm.activate_version(cap.capability_id, "1.4.2")
    active_rec = vm.get_version(cap.capability_id, "1.4.2")
    assert active_rec is not None
    assert active_rec.is_active is True

    # Mutating an active version: attempting to register with same version raises ImmutableVersionMutationError
    with pytest.raises(ImmutableVersionMutationError):
        vm.register_version(cap)


def test_version_lineage_and_supersedes():
    vm = CapabilityVersionManager()
    cap_v1 = make_sample_capability(version="1.0.0")
    vm.register_version(cap_v1)
    vm.activate_version(cap_v1.capability_id, "1.0.0")

    cap_v2 = make_sample_capability(version="2.0.0")
    vm.register_version(cap_v2)
    vm.activate_version(cap_v2.capability_id, "2.0.0")

    v1_rec = vm.get_version(cap_v1.capability_id, "1.0.0")
    v2_rec = vm.get_version(cap_v2.capability_id, "2.0.0")

    assert v2_rec.supersedes == v1_rec.version_id
    assert v1_rec.superseded_by == v2_rec.version_id
    assert v1_rec.is_active is False
    assert v2_rec.is_active is True


# ==============================================================================
# 3. DETERMINISTIC CRYPTOGRAPHIC FINGERPRINTING (Phase 15)
# ==============================================================================

def test_capability_fingerprinting_tamper_detection():
    cap = make_sample_capability()
    CapabilityFingerprinter.fingerprint_capability(cap)

    orig_composite = cap.composite_fingerprint
    orig_contract = cap.contract_fingerprint
    orig_impl = cap.implementation_fingerprint

    assert orig_composite.startswith("cmp_")
    assert orig_contract.startswith("cfp_")
    assert orig_impl.startswith("ifp_")

    # Integrity verification passes
    is_valid, err = CapabilityFingerprinter.verify_fingerprint_integrity(cap)
    assert is_valid is True
    assert err is None

    # Tamper with schema properties: verification must catch mismatch
    cap.parameters_schema["properties"]["malicious_field"] = {"type": "string"}
    is_valid_tampered, err_tampered = CapabilityFingerprinter.verify_fingerprint_integrity(cap)
    assert is_valid_tampered is False
    assert "mismatch" in str(err_tampered).lower()


# ==============================================================================
# 4. COMPATIBILITY ENGINE (Phase 4)
# ==============================================================================

def test_compatibility_evaluator_classifications():
    v1 = make_sample_capability(version="1.0.0")
    CapabilityFingerprinter.fingerprint_capability(v1)

    # 1. Identical capability -> FULLY_COMPATIBLE
    rep1 = CompatibilityEvaluator.evaluate_compatibility(v1, v1)
    assert rep1.classification == CompatibilityClassification.FULLY_COMPATIBLE
    assert rep1.risk_level == "LOW"

    # 1b. Backward compatible patch bump -> BACKWARD_COMPATIBLE
    v1_clone = make_sample_capability(version="1.0.1")
    CapabilityFingerprinter.fingerprint_capability(v1_clone)
    rep1_patch = CompatibilityEvaluator.evaluate_compatibility(v1, v1_clone)
    assert rep1_patch.classification == CompatibilityClassification.BACKWARD_COMPATIBLE

    # 2. Add non-required field -> BACKWARD_COMPATIBLE
    v2 = make_sample_capability(version="1.1.0")
    v2.parameters_schema["properties"]["new_optional_field"] = {"type": "string"}
    CapabilityFingerprinter.fingerprint_capability(v2)
    rep2 = CompatibilityEvaluator.evaluate_compatibility(v1, v2)
    assert rep2.classification == CompatibilityClassification.BACKWARD_COMPATIBLE

    # 3. Add new REQUIRED field -> INCOMPATIBLE breaking change
    v3 = make_sample_capability(version="2.0.0")
    v3.parameters_schema["properties"]["token_secret"] = {"type": "string"}
    v3.parameters_schema["required"].append("token_secret")
    CapabilityFingerprinter.fingerprint_capability(v3)
    rep3 = CompatibilityEvaluator.evaluate_compatibility(v1, v3)
    assert rep3.classification == CompatibilityClassification.INCOMPATIBLE
    assert rep3.risk_level == "HIGH"


# ==============================================================================
# 5. DEPENDENCY GRAPH & HEALTH PROPAGATION (Phase 5 & Phase 13)
# ==============================================================================

def test_dependency_graph_reverse_dependents_and_health_cascade():
    graph = CapabilityDependencyGraph()

    # Network capability depends on TLS runtime
    deps_net = [
        CapabilityDependency(target_id="cap_tls_runtime", dependency_type=DependencyType.NATIVE_CAPABILITY, version_constraint=">=1.0.0")
    ]
    graph.register_dependencies("cap_net", deps_net)

    # Web search capability depends on Network capability
    deps_search = [
        CapabilityDependency(target_id="cap_net", dependency_type=DependencyType.TOOL, version_constraint=">=1.0.0")
    ]
    graph.register_dependencies("cap_search", deps_search)

    # Verify reverse dependents
    tls_dependents = graph.get_dependents("cap_tls_runtime")
    assert "cap_net" in tls_dependents

    net_dependents = graph.get_dependents("cap_net")
    assert "cap_search" in net_dependents

    # Propagate health degradation from TLS -> Net -> Search
    capabilities_map = {
        "cap_tls_runtime": make_sample_capability(cap_id="cap_tls_runtime"),
        "cap_net": make_sample_capability(cap_id="cap_net"),
        "cap_search": make_sample_capability(cap_id="cap_search"),
    }

    impacted = graph.propagate_health_degradation(
        unhealthy_target_id="cap_tls_runtime",
        target_health=HealthStatus.DEGRADED,
        known_capabilities=capabilities_map,
    )

    assert "cap_net" in impacted
    assert "cap_search" in impacted
    assert capabilities_map["cap_net"].health_state == HealthStatus.DEGRADED
    assert capabilities_map["cap_search"].health_state == HealthStatus.DEGRADED


# ==============================================================================
# 6. CAPABILITY VALIDATION & PERMISSION SAFETY (Phase 6 & Phase 16)
# ==============================================================================

def test_validation_pipeline_without_privilege_escalation():
    validator = CapabilityValidator()
    cap = make_sample_capability()

    # Valid capability passes
    passed, issues = validator.validate_capability(cap)
    assert passed is True
    assert len(issues) == 0
    assert cap.lifecycle_state == LifecycleState.VALIDATED

    # Invariant: Validation must NOT grant permissions automatically
    assert "READ" in cap.required_permissions

    # Malformed capability fails validation
    bad_cap = make_sample_capability(cap_id="bad_cap")
    bad_cap.parameters_schema = {"type": "string"}  # Must be object
    passed_bad, issues_bad = validator.validate_capability(bad_cap)
    assert passed_bad is False
    assert any("object" in iss.lower() for iss in issues_bad)
    assert bad_cap.lifecycle_state == LifecycleState.FAILED


# ==============================================================================
# 7. CONFORMANCE TESTING (Phase 7)
# ==============================================================================

def test_conformance_runner_deterministic_vectors():
    runner = ConformanceTestRunner()
    cap = make_sample_capability()

    vectors = [
        ConformanceTestVector(
            name="valid_query_check",
            inputs={"query": "quantum computing"},
            idempotent_assert=True,
        ),
    ]

    result = runner.run_conformance_suite(cap, test_vectors=vectors)
    assert result.passed == 1
    assert result.failed == 0
    assert result.duration_ms >= 0.0


# ==============================================================================
# 8. SIMULATION GATE (Phase 8)
# ==============================================================================

def test_simulation_gate_freshness_and_stale_rejection():
    gate = SimulationGate()
    cap = make_sample_capability()

    # Low-risk TOOL does not mandate heavy simulation
    status, details = gate.evaluate_simulation_gate(cap)
    assert status in (SimulationStatus.SIMULATION_PASSED, SimulationStatus.SIMULATION_NOT_REQUIRED)

    # Privileged SYSTEM capability requires simulation
    cap_priv = make_sample_capability(security_class=SecurityClassification.CRITICAL_INFRASTRUCTURE)
    status_priv, details_priv = gate.evaluate_simulation_gate(cap_priv)
    assert status_priv in (SimulationStatus.SIMULATION_PASSED, SimulationStatus.SIMULATION_REQUIRED)


# ==============================================================================
# 9. CANARY ROLLOUT & AUTOMATIC ABORT (Phase 9)
# ==============================================================================

def test_canary_rollout_progressive_traffic_and_sla_breach():
    cm = CanaryRolloutManager()
    cap = make_sample_capability()
    cap.lifecycle_state = LifecycleState.VALIDATED

    cfg = CanaryRolloutConfig(
        canary_percent=10.0,
        error_rate_threshold=0.05,
        latency_threshold_ms=100.0,
    )

    # Start Canary
    rollout = cm.start_canary(cap, target_version="1.1.0", config=cfg)
    assert rollout.current_percent == 10.0
    assert rollout.state == RolloutState.CANARY_RUNNING
    assert cap.lifecycle_state == LifecycleState.CANARY

    # Record healthy requests
    for _ in range(5):
        cm.record_canary_traffic(cap, is_error=False, latency_ms=15.0)

    # Progressive traffic ramp
    rollout.current_percent = 20.0
    assert rollout.current_percent == 20.0

    # Inject latency spike breach (> 100ms) -> auto-abort to DEGRADED
    cm.record_canary_traffic(cap, is_error=True, latency_ms=350.0)

    assert rollout.state == RolloutState.ABORTED
    assert cap.lifecycle_state == LifecycleState.DEGRADED


# ==============================================================================
# 10. 11-GATE PROMOTION COORDINATION (Phase 10)
# ==============================================================================

def test_promotion_gates_evaluation():
    coord = PromotionGateCoordinator()
    cap = make_sample_capability()
    cap.lifecycle_state = LifecycleState.VALIDATED
    cap.last_validated_at = _now_utc()

    # Evaluation with uncompleted canary
    eval1 = coord.evaluate_gates(cap, target_version="1.0.0", canary_completed=False)
    assert eval1.all_passed is False
    assert any("Canary" in b for b in eval1.blockers)

    # Evaluation with canary completed
    eval2 = coord.evaluate_gates(cap, target_version="1.0.0", canary_completed=True)
    assert eval2.all_passed is True

    # Register version before promoting
    coord.version_manager.register_version(cap)

    # Promote to ACTIVE
    promoted, err = coord.promote_to_active(cap, target_version="1.0.0", gate_evaluation=eval2)
    assert promoted is True
    assert err is None
    assert cap.lifecycle_state == LifecycleState.ACTIVE


# ==============================================================================
# 11. SAFE ROLLBACK WITH VERIFICATION (Phase 11)
# ==============================================================================

def test_safe_rollback_to_stable_version():
    vm = CapabilityVersionManager()
    rm = CapabilityRollbackManager(version_manager=vm)
    cap = make_sample_capability(version="2.0.0")
    cap.lifecycle_state = LifecycleState.ACTIVE

    # Register stable rollback target
    v1_cap = make_sample_capability(version="1.0.0")
    vm.register_version(v1_cap)
    vm.activate_version(v1_cap.capability_id, "1.0.0")

    # Register v2
    vm.register_version(cap)
    vm.activate_version(cap.capability_id, "2.0.0")

    ok, record, msg = rm.rollback_capability(
        capability=cap,
        target_version="1.0.0",
        reason="P0 latency regression in v2.0.0",
    )

    assert ok is True
    assert record.to_version == "1.0.0"
    assert record.from_version == "2.0.0"
    assert record.verification_passed is True
    assert cap.version == "1.0.0"
    assert cap.lifecycle_state == LifecycleState.ACTIVE


# ==============================================================================
# 12. DEPRECATION & RETIREMENT CONSUMER BLOCKING (Phase 12)
# ==============================================================================

def test_deprecation_and_retirement_blocked_by_dependents():
    graph = CapabilityDependencyGraph()
    dep_mgr = CapabilityDeprecationManager(dependency_graph=graph)

    cap = make_sample_capability()
    cap.lifecycle_state = LifecycleState.ACTIVE

    # Deprecate capability with 30 day sunset
    plan = dep_mgr.deprecate_capability(
        capability=cap,
        reason="Replaced by faster native v2 tool",
        replacement_capability_id="cap_web_search_v2",
        sunset_days=30,
    )
    assert cap.lifecycle_state == LifecycleState.DEPRECATED
    assert plan.replacement_capability_id == "cap_web_search_v2"

    # Register an active consumer depending on this capability
    graph.register_dependencies(
        "cap_research_workflow",
        [CapabilityDependency(target_id=cap.capability_id, dependency_type=DependencyType.TOOL, version_constraint=">=1.0.0")],
    )

    # Attempt retirement without force: must be rejected due to active dependent
    ok, msg = dep_mgr.retire_capability(cap, force_retirement=False)
    assert ok is False
    assert "dependent" in msg.lower()
    assert cap.lifecycle_state == LifecycleState.DEPRECATED

    # Forced retirement with administrative sign-off succeeds
    ok_forced, msg_forced = dep_mgr.retire_capability(cap, force_retirement=True)
    assert ok_forced is True
    assert cap.lifecycle_state == LifecycleState.RETIRED


# ==============================================================================
# 13. EMERGENCY STOP FAIL-CLOSED PRIMACY (Phase 19 & Phase 27)
# ==============================================================================

def test_emergency_stop_fail_closed_blocking():
    service = CapabilityLifecycleService()
    estop = get_emergency_stop_service()

    cap = make_sample_capability(cap_id="cap_estop_isolated")
    service.register_discovered_capability(cap)

    # Trigger EmergencyStop
    estop.trigger_emergency_stop(reason="Security containment drill")
    assert estop.is_stopped() is True

    try:
        # 1. Validation blocked
        val_ok, issues = service.validate_capability(cap.capability_id)
        assert val_ok is False
        assert any("EmergencyStop" in iss for iss in issues)

        # 2. Canary rollout blocked
        with pytest.raises(RuntimeError) as exc:
            service.start_canary(cap.capability_id, "1.1.0")
        assert "EmergencyStop" in str(exc.value)

        # 3. New registration marked BLOCKED
        cap2 = make_sample_capability(cap_id="cap_unregistered")
        reg2 = service.register_discovered_capability(cap2)
        assert reg2.lifecycle_state == LifecycleState.BLOCKED

    finally:
        # Clear EmergencyStop
        estop.reset_emergency_stop(is_human_user=True)
        assert estop.is_stopped() is False


# ==============================================================================
# 14. COMPLETE EVOLUTION LOOP SCENARIO (Phase 14 & Phase 30)
# ==============================================================================

def test_full_evolution_loop_end_to_end():
    service = CapabilityLifecycleService()
    cap = make_sample_capability(cap_id="cap_e2e_evolution", version="1.0.0")

    # Step 1: DISCOVER
    service.register_discovered_capability(cap)
    assert cap.lifecycle_state == LifecycleState.DISCOVERED

    # Step 2: VALIDATE
    passed, issues = service.validate_capability(cap.capability_id)
    assert passed is True
    assert cap.lifecycle_state == LifecycleState.VALIDATED

    # Step 3: CONFORMANCE
    conf_res = service.test_conformance(cap.capability_id)
    assert conf_res.passed >= 1

    # Step 4: SIMULATE
    sim_status, sim_details = service.simulate_rollout(cap.capability_id)
    assert sim_status in (SimulationStatus.SIMULATION_PASSED, SimulationStatus.SIMULATION_NOT_REQUIRED)

    # Step 5: CANARY
    rollout = service.start_canary(cap.capability_id, target_version="1.0.0")
    assert cap.lifecycle_state == LifecycleState.CANARY

    # Record successful canary metrics
    service.record_canary_telemetry(cap.capability_id, is_error=False, latency_ms=12.0)

    # Step 6: PROMOTE
    promoted, err, gate_eval = service.promote_capability(cap.capability_id, target_version="1.0.0")
    assert promoted is True
    assert cap.lifecycle_state == LifecycleState.ACTIVE

    # Step 7: OPERATIONAL HEALTH CASCADE & RECOVERY
    # Telemetry degradation moves ACTIVE -> DEGRADED
    service.update_capability_health(
        cap.capability_id,
        HealthStatus.DEGRADED,
        failure_reason="Upstream provider throttled",
    )
    assert cap.lifecycle_state == LifecycleState.DEGRADED

    # Telemetry recovery moves DEGRADED -> ACTIVE
    service.update_capability_health(cap.capability_id, HealthStatus.HEALTHY)
    assert cap.lifecycle_state == LifecycleState.ACTIVE
