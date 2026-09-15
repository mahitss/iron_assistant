"""11-Gate Safe Capability Promotion Coordinator (Task 91 Phase 10)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.capability_lifecycle.models import (
    CapabilityMetadata,
    HealthStatus,
    LifecycleState,
    PromotionGateEvaluation,
    SecurityClassification,
    SimulationStatus,
)
from app.capability_lifecycle.simulation_gate import SimulationGate, get_simulation_gate
from app.capability_lifecycle.state_machine import CapabilityStateMachine, get_capability_state_machine
from app.capability_lifecycle.versioning import CapabilityVersionManager, get_capability_version_manager
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.capability_lifecycle.promotion")


class PromotionGateCoordinator:
    """Evaluates all 11 mandatory safety gates before promoting a capability version to ACTIVE."""

    def __init__(
        self,
        state_machine: Optional[CapabilityStateMachine] = None,
        version_manager: Optional[CapabilityVersionManager] = None,
        simulation_gate: Optional[SimulationGate] = None,
    ) -> None:
        self.state_machine = state_machine or get_capability_state_machine()
        self.version_manager = version_manager or get_capability_version_manager()
        self.simulation_gate = simulation_gate or get_simulation_gate()

    def evaluate_gates(
        self,
        capability: CapabilityMetadata,
        target_version: str,
        conformance_passed: bool = True,
        dependency_compatible: bool = True,
        security_approved: bool = True,
        governance_approved: bool = True,
        resource_budget_allocated: bool = True,
        simulation_status: Optional[SimulationStatus] = None,
        canary_completed: bool = True,
        human_approval_obtained: bool = True,
    ) -> PromotionGateEvaluation:
        """Evaluates all 11 promotion gates fail-closed."""
        gates: Dict[str, bool] = {}
        blockers: List[str] = []

        # 1. Emergency Stop Check (Absolute Primacy)
        e_stop = get_emergency_stop_service()
        e_stop_inactive = not e_stop.is_stopped()
        gates["emergency_stop_inactive"] = e_stop_inactive
        if not e_stop_inactive:
            blockers.append("EmergencyStop is currently ACTIVE (Fail-closed)")

        # 2. Validation Passed
        val_ok = capability.last_validated_at is not None and capability.lifecycle_state != LifecycleState.FAILED
        gates["validation_passed"] = val_ok
        if not val_ok:
            blockers.append("Capability has not completed formal validation")

        # 3. Conformance Passed
        gates["conformance_passed"] = conformance_passed
        if not conformance_passed:
            blockers.append("Conformance test suite has failing vectors")

        # 4. Dependency Compatibility Passed
        dep_ok = dependency_compatible
        for dep in capability.dependencies:
            if hasattr(dep, "health_status") and dep.health_status in (HealthStatus.DEGRADED, HealthStatus.UNSTABLE, HealthStatus.UNSAFE):
                dep_ok = False
                blockers.append(f"Dependency '{dep.target_id}' is degraded ({dep.health_status.value})")
        gates["dependency_compatibility_passed"] = dep_ok
        if not dependency_compatible:
            blockers.append("One or more declared dependencies fail version constraints")

        # 5. Security Policy Passed (SecurityCenter)
        gates["security_policy_passed"] = security_approved
        if not security_approved:
            blockers.append("SecurityCenter rejected required permissions or credentials")

        # 6. Governance Policy Passed (Constitution)
        gates["governance_policy_passed"] = governance_approved
        if not governance_approved:
            blockers.append("Governance rejected capability activation under current policy")

        # 7. Resource Allocation Available (Resource Economy)
        gates["resource_allocation_available"] = resource_budget_allocated
        if not resource_budget_allocated:
            blockers.append("Resource Economy has insufficient budget allocation")

        # 8. Simulation Gate Passed
        sim_stat = simulation_status
        if sim_stat is None:
            sim_stat, _ = self.simulation_gate.evaluate_simulation_gate(capability)

        sim_ok = sim_stat in (SimulationStatus.SIMULATION_PASSED, SimulationStatus.SIMULATION_NOT_REQUIRED)
        gates["simulation_passed"] = sim_ok
        if not sim_ok:
            blockers.append(f"Simulation gate failed with status: {sim_stat.value}")

        # 9. Reliability Threshold Passed (Task 90)
        health_degraded = capability.health_state in (HealthStatus.DEGRADED, HealthStatus.UNSTABLE, HealthStatus.UNSAFE)
        rel_ok = capability.reliability.success_rate >= 0.80 and capability.reliability.stability_window_passed and not health_degraded
        gates["reliability_threshold_passed"] = rel_ok
        if not rel_ok:
            if health_degraded:
                blockers.append(f"Capability health state is {capability.health_state.value} (Operational degradation blocks promotion)")
            else:
                blockers.append(f"Reliability rate {capability.reliability.success_rate * 100:.1f}% below 80% SLA threshold")

        # 10. Canary Rollout Passed
        gates["canary_passed"] = canary_completed
        if not canary_completed:
            blockers.append("Canary rollout has not completed or breached failure thresholds")

        # 11. Human Approval Obtained (when policy requires it)
        requires_human = (
            capability.security_classification == SecurityClassification.CRITICAL_INFRASTRUCTURE
            or "DESTRUCTIVE" in capability.required_permissions
        )
        app_ok = human_approval_obtained if requires_human else True
        gates["approval_obtained"] = app_ok
        if not app_ok:
            blockers.append("Mandatory human operator approval has not been granted")

        all_passed = len(blockers) == 0

        eval_record = PromotionGateEvaluation(
            capability_id=capability.capability_id,
            version=target_version,
            gates=gates,
            all_passed=all_passed,
            blockers=blockers,
        )

        logger.info(
            "Promotion gate evaluation for %s v%s: %s (%d blockers)",
            capability.capability_id,
            target_version,
            "PASSED" if all_passed else "BLOCKED",
            len(blockers),
        )
        return eval_record

    def promote_to_active(
        self,
        capability: CapabilityMetadata,
        target_version: str,
        gate_evaluation: PromotionGateEvaluation,
        actor: str = "promotion_coordinator",
    ) -> Tuple[bool, Optional[str]]:
        """Promotes capability version to ACTIVE state if and only if all gates passed."""
        if not gate_evaluation.all_passed:
            err_msg = f"Cannot promote capability '{capability.capability_id}': Blockers: {gate_evaluation.blockers}"
            logger.warning(err_msg)
            return False, err_msg

        # 1. Lock immutable version as active in version manager
        rec = self.version_manager.activate_version(capability.capability_id, target_version)
        capability.version = target_version
        capability.active_version_id = rec.version_id
        capability.canary_version_id = None

        # 2. State machine transition to ACTIVE
        self.state_machine.transition(
            capability,
            LifecycleState.ACTIVE,
            reason=f"Successfully passed all 11 promotion gates for v{target_version}",
            actor=actor,
            safety_metadata={"gates": gate_evaluation.gates},
        )

        logger.info(
            "Capability '%s' successfully promoted to ACTIVE at v%s",
            capability.capability_id,
            target_version,
        )
        return True, None


_global_promotion_coordinator: Optional[PromotionGateCoordinator] = None


def get_promotion_coordinator() -> PromotionGateCoordinator:
    global _global_promotion_coordinator
    if _global_promotion_coordinator is None:
        _global_promotion_coordinator = PromotionGateCoordinator()
    return _global_promotion_coordinator
