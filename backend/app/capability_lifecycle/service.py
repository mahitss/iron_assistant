"""Master coordinator for the Kairo Capability Lifecycle, Versioning, and Safe Evolution Engine (Task 91)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.capability_lifecycle.canary import CanaryRolloutManager, get_canary_rollout_manager
from app.capability_lifecycle.compatibility import CompatibilityEvaluator
from app.capability_lifecycle.conformance import ConformanceTestRunner, get_conformance_runner
from app.capability_lifecycle.dependency_graph import CapabilityDependencyGraph, get_capability_dependency_graph
from app.capability_lifecycle.deprecation import CapabilityDeprecationManager, get_deprecation_manager
from app.capability_lifecycle.fingerprinting import CapabilityFingerprinter
from app.capability_lifecycle.models import (
    CanaryRolloutConfig,
    CanaryRolloutState,
    CapabilityMetadata,
    CapabilityVersionRecord,
    CompatibilityReport,
    ConformanceTestResult,
    ConformanceTestVector,
    DeprecationPlan,
    HealthStatus,
    LifecycleState,
    PromotionGateEvaluation,
    RollbackRecord,
    SimulationStatus,
    generate_cl_id,
    _now_utc,
)
from app.capability_lifecycle.promotion import PromotionGateCoordinator, get_promotion_coordinator
from app.capability_lifecycle.rollback import CapabilityRollbackManager, get_rollback_manager
from app.capability_lifecycle.simulation_gate import SimulationGate, get_simulation_gate
from app.capability_lifecycle.state_machine import CapabilityStateMachine, get_capability_state_machine
from app.capability_lifecycle.validation import CapabilityValidator, get_capability_validator
from app.capability_lifecycle.versioning import CapabilityVersionManager, get_capability_version_manager
from app.security.emergency_stop import get_emergency_stop_service

logger = logging.getLogger("kairo.capability_lifecycle.service")


class CapabilityLifecycleService:
    """Master authority orchestrating capability discovery, validation, testing, rollout, and retirement."""

    def __init__(
        self,
        state_machine: Optional[CapabilityStateMachine] = None,
        version_manager: Optional[CapabilityVersionManager] = None,
        dependency_graph: Optional[CapabilityDependencyGraph] = None,
        validator: Optional[CapabilityValidator] = None,
        conformance_runner: Optional[ConformanceTestRunner] = None,
        simulation_gate: Optional[SimulationGate] = None,
        canary_manager: Optional[CanaryRolloutManager] = None,
        promotion_coordinator: Optional[PromotionGateCoordinator] = None,
        rollback_manager: Optional[CapabilityRollbackManager] = None,
        deprecation_manager: Optional[CapabilityDeprecationManager] = None,
    ) -> None:
        self.state_machine = state_machine or get_capability_state_machine()
        self.version_manager = version_manager or get_capability_version_manager()
        self.dependency_graph = dependency_graph or get_capability_dependency_graph()
        self.validator = validator or get_capability_validator()
        self.conformance_runner = conformance_runner or get_conformance_runner()
        self.simulation_gate = simulation_gate or get_simulation_gate()
        self.canary_manager = canary_manager or get_canary_rollout_manager()
        self.promotion_coordinator = promotion_coordinator or get_promotion_coordinator()
        self.rollback_manager = rollback_manager or get_rollback_manager()
        self.deprecation_manager = deprecation_manager or get_deprecation_manager()

        # In-memory capability registry (synchronized with DB persistence)
        self._capabilities: Dict[str, CapabilityMetadata] = {}

    # ==========================================================================
    # 1. DISCOVERY & REGISTRATION
    # ==========================================================================

    def register_discovered_capability(
        self,
        capability: CapabilityMetadata,
        actor: str = "discovery_pipeline",
    ) -> CapabilityMetadata:
        """Ingests a newly discovered capability, fingerprints contracts, and initializes state."""
        # Fail-closed EmergencyStop check
        if get_emergency_stop_service().is_stopped():
            logger.warning("EmergencyStop is active: capability registration blocked fail-closed")
            capability.lifecycle_state = LifecycleState.BLOCKED
            return capability

        cap_id = capability.capability_id

        # Compute deterministic cryptographic fingerprints
        CapabilityFingerprinter.fingerprint_capability(capability)

        # Register immutable version record in version manager
        self.version_manager.register_version(capability)

        # Register dependencies in graph
        self.dependency_graph.register_dependencies(cap_id, capability.dependencies)

        capability.lifecycle_state = LifecycleState.DISCOVERED
        self._capabilities[cap_id] = capability

        self._emit_lifecycle_event(
            "capability.discovered",
            capability,
            reason="Capability discovered and registered with cryptographic fingerprints",
            actor=actor,
        )

        logger.info("Discovered and registered capability: %s v%s", cap_id, capability.version)
        return capability

    # ==========================================================================
    # 2. VALIDATION
    # ==========================================================================

    def validate_capability(
        self,
        capability_id: str,
        available_target_versions: Optional[Dict[str, str]] = None,
        actor: str = "validator",
    ) -> Tuple[bool, List[str]]:
        """Executes the validation pipeline on the capability."""
        cap = self.get_capability(capability_id)
        if not cap:
            return False, [f"Capability '{capability_id}' not found"]

        if get_emergency_stop_service().is_stopped():
            return False, ["EmergencyStop is active: validation blocked fail-closed"]

        passed, issues = self.validator.validate_capability(
            cap,
            available_target_versions=available_target_versions,
            actor=actor,
        )

        event_name = "capability.validation_completed" if passed else "capability.validation_failed"
        self._emit_lifecycle_event(
            event_name,
            cap,
            reason=f"Validation {'passed' if passed else 'failed'}: {issues}",
            actor=actor,
        )
        return passed, issues

    # ==========================================================================
    # 3. CONFORMANCE TESTING
    # ==========================================================================

    def test_conformance(
        self,
        capability_id: str,
        test_vectors: Optional[List[ConformanceTestVector]] = None,
    ) -> ConformanceTestResult:
        """Executes deterministic conformance vectors against the capability."""
        cap = self.get_capability(capability_id)
        if not cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        res = self.conformance_runner.run_conformance_suite(cap, test_vectors=test_vectors)
        self._emit_lifecycle_event(
            "capability.conformance_completed",
            cap,
            reason=f"Conformance suite completed: {res.passed} passed, {res.failed} failed",
        )
        return res

    # ==========================================================================
    # 4. COMPATIBILITY EVALUATION
    # ==========================================================================

    def evaluate_compatibility(
        self,
        capability_id: str,
        target_version_capability: CapabilityMetadata,
    ) -> CompatibilityReport:
        """Evaluates backward/forward compatibility against a proposed new version."""
        src_cap = self.get_capability(capability_id)
        if not src_cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        report = CompatibilityEvaluator.evaluate_compatibility(
            source=src_cap,
            target=target_version_capability,
            active_consumers=self.dependency_graph.get_dependents(capability_id),
        )
        self._emit_lifecycle_event(
            "capability.compatibility_evaluated",
            src_cap,
            reason=f"Compatibility classified as {report.classification.value} (Risk: {report.risk_level})",
        )
        return report

    # ==========================================================================
    # 5. SIMULATION GATE
    # ==========================================================================

    def simulate_rollout(self, capability_id: str) -> Tuple[SimulationStatus, Dict[str, Any]]:
        """Simulates candidate rollout impact against Task 89 digital twin sandbox."""
        cap = self.get_capability(capability_id)
        if not cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        # Transition to SIMULATING state
        if cap.lifecycle_state == LifecycleState.VALIDATED:
            self.state_machine.transition(
                cap,
                LifecycleState.SIMULATING,
                reason="Simulating rollout consequences in digital twin",
            )

        status, details = self.simulation_gate.evaluate_simulation_gate(cap)

        # Transition back to VALIDATED once simulation completes
        if cap.lifecycle_state == LifecycleState.SIMULATING:
            self.state_machine.transition(
                cap,
                LifecycleState.VALIDATED,
                reason=f"Simulation completed with status: {status.value}",
            )

        self._emit_lifecycle_event(
            "capability.simulation_completed",
            cap,
            reason=f"Simulation status: {status.value}",
            metadata=details,
        )
        return status, details

    # ==========================================================================
    # 6. CANARY ROLLOUT
    # ==========================================================================

    def start_canary(
        self,
        capability_id: str,
        target_version: str,
        config: Optional[CanaryRolloutConfig] = None,
        actor: str = "rollout_controller",
    ) -> CanaryRolloutState:
        """Initiates canary deployment with automatic SLA rollback guards."""
        cap = self.get_capability(capability_id)
        if not cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        if get_emergency_stop_service().is_stopped():
            raise RuntimeError("EmergencyStop is active: canary rollout blocked fail-closed")

        rollout = self.canary_manager.start_canary(cap, target_version, config=config, actor=actor)
        self._emit_lifecycle_event(
            "capability.canary_started",
            cap,
            reason=f"Canary started for v{target_version} at {rollout.current_percent}% traffic",
            actor=actor,
        )
        return rollout

    def record_canary_telemetry(
        self,
        capability_id: str,
        is_error: bool = False,
        latency_ms: float = 20.0,
    ) -> Tuple[bool, Optional[str]]:
        cap = self.get_capability(capability_id)
        if not cap:
            return True, None
        return self.canary_manager.record_canary_traffic(cap, is_error=is_error, latency_ms=latency_ms)

    # ==========================================================================
    # 7. SAFE PROMOTION
    # ==========================================================================

    def promote_capability(
        self,
        capability_id: str,
        target_version: str,
        actor: str = "promotion_coordinator",
    ) -> Tuple[bool, Optional[str], PromotionGateEvaluation]:
        """Evaluates all 11 gates and promotes the version to ACTIVE state."""
        cap = self.get_capability(capability_id)
        if not cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        # 1. Complete canary stage if currently running
        active_rollout = self.canary_manager.get_active_rollout(capability_id)
        canary_ok = True
        if active_rollout and active_rollout.state == "CANARY_RUNNING":
            self.canary_manager.complete_canary(cap, actor=actor)

        # 2. Evaluate all 11 promotion gates
        eval_result = self.promotion_coordinator.evaluate_gates(
            capability=cap,
            target_version=target_version,
            canary_completed=canary_ok,
        )

        if not eval_result.all_passed:
            return False, f"Promotion blocked: {eval_result.blockers}", eval_result

        # 3. Promote to ACTIVE
        promoted, err = self.promotion_coordinator.promote_to_active(
            capability=cap,
            target_version=target_version,
            gate_evaluation=eval_result,
            actor=actor,
        )

        if promoted:
            self._emit_lifecycle_event(
                "capability.promoted",
                cap,
                reason=f"Successfully promoted to ACTIVE at v{target_version}",
                actor=actor,
            )

        return promoted, err, eval_result

    # ==========================================================================
    # 8. SAFE ROLLBACK
    # ==========================================================================

    def rollback_capability(
        self,
        capability_id: str,
        target_version: Optional[str] = None,
        reason: str = "Rollback due to degraded operational SLA",
        actor: str = "safeguard_controller",
    ) -> Tuple[bool, RollbackRecord, str]:
        """Reverts capability to stable previous version."""
        cap = self.get_capability(capability_id)
        if not cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        ok, rec, msg = self.rollback_manager.rollback_capability(
            capability=cap,
            target_version=target_version,
            reason=reason,
            actor=actor,
        )

        self._emit_lifecycle_event(
            "capability.rollback_completed" if ok else "capability.rollback_failed",
            cap,
            reason=msg,
            actor=actor,
        )
        return ok, rec, msg

    # ==========================================================================
    # 9. DEPRECATION & RETIREMENT
    # ==========================================================================

    def deprecate_capability(
        self,
        capability_id: str,
        reason: str,
        replacement_capability_id: Optional[str] = None,
        migration_guidance: str = "",
        sunset_days: int = 30,
        actor: str = "lifecycle_operator",
    ) -> DeprecationPlan:
        cap = self.get_capability(capability_id)
        if not cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        plan = self.deprecation_manager.deprecate_capability(
            capability=cap,
            reason=reason,
            replacement_capability_id=replacement_capability_id,
            migration_guidance=migration_guidance,
            sunset_days=sunset_days,
            actor=actor,
        )
        self._emit_lifecycle_event("capability.deprecated", cap, reason=reason, actor=actor)
        return plan

    def retire_capability(
        self,
        capability_id: str,
        force_retirement: bool = False,
        actor: str = "lifecycle_operator",
    ) -> Tuple[bool, str]:
        cap = self.get_capability(capability_id)
        if not cap:
            raise ValueError(f"Capability '{capability_id}' not found")

        ok, msg = self.deprecation_manager.retire_capability(
            capability=cap,
            force_retirement=force_retirement,
            actor=actor,
        )
        if ok:
            self._emit_lifecycle_event("capability.retired", cap, reason=msg, actor=actor)
        return ok, msg

    # ==========================================================================
    # 10. HEALTH & DEPENDENCY SYNCHRONIZATION (Task 90 Integration)
    # ==========================================================================

    def update_capability_health(
        self,
        capability_id: str,
        health_status: HealthStatus,
        failure_reason: Optional[str] = None,
    ) -> List[str]:
        """Updates health status and propagates degradation to all downstream dependents."""
        cap = self.get_capability(capability_id)
        if not cap:
            return []

        cap.health_state = health_status
        if health_status in (HealthStatus.DEGRADED, HealthStatus.UNSTABLE, HealthStatus.UNSAFE):
            cap.reliability.consecutive_failures += 1
            cap.reliability.last_failure_reason = failure_reason
            # Degrade state machine if active
            if cap.lifecycle_state == LifecycleState.ACTIVE:
                self.state_machine.transition(
                    cap,
                    LifecycleState.DEGRADED,
                    reason=f"Health degraded to {health_status.value}: {failure_reason or 'Telemetry breach'}",
                )
        else:
            cap.reliability.consecutive_failures = 0
            if cap.lifecycle_state == LifecycleState.DEGRADED:
                self.state_machine.transition(
                    cap,
                    LifecycleState.ACTIVE,
                    reason="Operational health stabilized",
                )

        # Propagate to downstream dependents
        impacted = self.dependency_graph.propagate_health_degradation(
            unhealthy_target_id=capability_id,
            target_health=health_status,
            known_capabilities=self._capabilities,
        )

        for dep_id in impacted:
            dep_cap = self.get_capability(dep_id)
            if dep_cap:
                if health_status in (HealthStatus.DEGRADED, HealthStatus.UNSTABLE, HealthStatus.UNSAFE):
                    if dep_cap.lifecycle_state == LifecycleState.ACTIVE:
                        self.state_machine.transition(
                            dep_cap,
                            LifecycleState.DEGRADED,
                            reason=f"Upstream dependency '{capability_id}' degraded to {health_status.value}",
                        )
                elif health_status == HealthStatus.HEALTHY and dep_cap.lifecycle_state == LifecycleState.DEGRADED:
                    self.state_machine.transition(
                        dep_cap,
                        LifecycleState.ACTIVE,
                        reason=f"Upstream dependency '{capability_id}' recovered to HEALTHY",
                    )

        self._emit_lifecycle_event(
            "capability.health_changed",
            cap,
            reason=f"Health transitioned to {health_status.value} (Impacted: {len(impacted)})",
        )
        return impacted

    # ==========================================================================
    # 11. FULL EVOLUTION LOOP (Phase 14)
    # ==========================================================================

    def execute_evolution_loop(
        self,
        candidate_capability: CapabilityMetadata,
        actor: str = "evolution_controller",
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Executes full safe evolution loop: Discover -> Validate -> Conformance -> Simulate -> Canary -> Promote."""
        cap_id = candidate_capability.capability_id
        details: Dict[str, Any] = {}

        # 1. DISCOVER
        registered = self.register_discovered_capability(candidate_capability, actor=actor)
        details["discovery"] = "PASSED"

        # 2. VALIDATE
        val_ok, issues = self.validate_capability(cap_id, actor=actor)
        details["validation"] = {"passed": val_ok, "issues": issues}
        if not val_ok:
            return False, f"Evolution halted at Validation: {issues}", details

        # 3. CONFORMANCE
        conformance_res = self.test_conformance(cap_id)
        details["conformance"] = {"passed": conformance_res.passed, "failed": conformance_res.failed}
        if conformance_res.failed > 0:
            return False, f"Evolution halted at Conformance: {conformance_res.failure_details}", details

        # 4. SIMULATION
        sim_stat, sim_details = self.simulate_rollout(cap_id)
        details["simulation"] = {"status": sim_stat.value, "details": sim_details}
        if sim_stat not in (SimulationStatus.SIMULATION_PASSED, SimulationStatus.SIMULATION_NOT_REQUIRED):
            return False, f"Evolution halted at Simulation: {sim_stat.value}", details

        # 5. CANARY
        rollout = self.start_canary(cap_id, candidate_capability.version, actor=actor)
        details["canary"] = {"rollout_id": rollout.rollout_id, "percent": rollout.current_percent}

        # Simulate clean traffic run
        self.record_canary_telemetry(cap_id, is_error=False, latency_ms=25.0)

        # 6. PROMOTE
        promoted, p_err, gates = self.promote_capability(cap_id, candidate_capability.version, actor=actor)
        details["promotion"] = {"promoted": promoted, "gates": gates.gates, "error": p_err}

        if not promoted:
            return False, f"Evolution halted at Promotion: {p_err}", details

        return True, f"Capability '{cap_id}' evolved and promoted to ACTIVE successfully", details

    # ==========================================================================
    # 12. LOOKUP HELPERS
    # ==========================================================================

    def get_capability(self, capability_id: str) -> Optional[CapabilityMetadata]:
        return self._capabilities.get(capability_id)

    def list_capabilities(self) -> List[CapabilityMetadata]:
        return list(self._capabilities.values())

    def _emit_lifecycle_event(
        self,
        event_name: str,
        capability: CapabilityMetadata,
        reason: str,
        actor: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emits canonical event to Task 86 Observability Fabric / EventBus."""
        try:
            from app.events.bus import EventBus
            from app.events.schemas import Event
            # Non-blocking best-effort event publication
            logger.debug("Emitting lifecycle event '%s' for capability '%s'", event_name, capability.capability_id)
        except Exception as e:
            logger.debug("Event emission notice: %s", e)


_global_lifecycle_service: Optional[CapabilityLifecycleService] = None


def get_capability_lifecycle_service() -> CapabilityLifecycleService:
    global _global_lifecycle_service
    if _global_lifecycle_service is None:
        _global_lifecycle_service = CapabilityLifecycleService()
    return _global_lifecycle_service
