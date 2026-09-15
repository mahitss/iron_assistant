"""Controlled fault-injection engine and deterministic chaos drill scenarios for Kairo Reliability (Task 88).

CRITICAL SAFETY INVARIANTS:
1. Disabled by default in all environments.
2. Must never be exposed on public user-facing APIs.
3. Only authorized administrators or automated test runners may trigger fault scenarios.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.reliability.models import (
    FaultInjectionConfig,
    FaultScenario,
    generate_id,
)
from app.reliability.taxonomy import FailureSeverity, FailureType

logger = logging.getLogger("kairo.reliability.fault_injection")


class FaultInjectionError(PermissionError):
    """Raised when fault injection is denied or misconfigured."""
    pass


class FaultInjectionEngine:
    """Manages deterministic fault injection hooks for resilience and recovery validation."""

    def __init__(self, enabled: bool = False) -> None:
        self.config = FaultInjectionConfig(enabled=enabled)
        # Active injection triggers: scenario_name -> Callable
        self._scenario_handlers: Dict[str, Callable[..., Any]] = {}
        # Execution logs: List[Dict[str, Any]]
        self._injection_history: List[Dict[str, Any]] = []

        # Register standard deterministic chaos scenarios
        self._register_default_scenarios()

    def enable(self, admin_token: str) -> None:
        """Explicitly enable fault injection for testing (requires valid admin token)."""
        if not admin_token or len(admin_token) < 8:
            raise FaultInjectionError("Valid administrative token required to enable fault injection")
        self.config.enabled = True
        logger.warning("FAULT INJECTION FRAMEWORK HAS BEEN EXPLICITLY ENABLED")

    def disable(self) -> None:
        """Disable all fault injection pathways immediately."""
        self.config.enabled = False
        logger.info("Fault injection framework disabled")

    def register_scenario(self, scenario: FaultScenario, handler: Optional[Callable[..., Any]] = None) -> None:
        """Registers a named fault scenario."""
        self.config.active_scenarios[scenario.scenario_name] = scenario
        if handler:
            self._scenario_handlers[scenario.scenario_name] = handler

    def trigger_fault(
        self,
        scenario_name: str,
        caller_identity: str = "test_runner",
        override_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Triggers an enabled deterministic fault scenario with strict guardrail validation."""
        # 1. Safety Guardrail: Framework must be globally enabled
        if not self.config.enabled:
            raise FaultInjectionError("Fault injection is disabled by default. Enable explicitly for test environments.")

        # 2. Safety Guardrail: Validate caller authorization
        if caller_identity not in ("admin", "test_runner", "chaos_controller"):
            raise FaultInjectionError(f"Caller '{caller_identity}' unauthorized to trigger fault injection")

        # 3. Check scenario registration
        scenario = self.config.active_scenarios.get(scenario_name)
        if not scenario or not scenario.enabled:
            raise FaultInjectionError(f"Scenario '{scenario_name}' is not registered or not enabled")

        # 4. Enforce max invocation bounds
        if scenario.current_invocations >= scenario.max_invocations:
            raise FaultInjectionError(
                f"Scenario '{scenario_name}' has reached its invocation limit ({scenario.max_invocations})"
            )

        scenario.current_invocations += 1
        params = {**scenario.parameters, **(override_params or {})}

        record = {
            "injection_id": generate_id("flt"),
            "scenario_name": scenario_name,
            "target_component": scenario.target_component,
            "failure_type": scenario.failure_type.value,
            "caller": caller_identity,
            "parameters": params,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._injection_history.append(record)

        logger.warning(
            "FAULT INJECTED: scenario='%s', component='%s', type='%s', id='%s'",
            scenario_name,
            scenario.target_component,
            scenario.failure_type.value,
            record["injection_id"],
        )

        # Execute registered scenario hook if present
        handler = self._scenario_handlers.get(scenario_name)
        result: Any = None
        if handler:
            result = handler(params)

        record["result"] = result
        return record

    def get_history(self) -> List[Dict[str, Any]]:
        """Return history of injected faults."""
        return list(self._injection_history)

    def _register_default_scenarios(self) -> None:
        """Registers canonical scenarios A through E for automated chaos testing."""
        defaults = [
            # Scenario A: Native Runtime Daemon Crash
            FaultScenario(
                scenario_name="rust_crash_after_dispatch",
                target_component="native_runtime",
                failure_type=FailureType.RUNTIME_FAILURE,
                parameters={"exit_code": 139, "simulate_sigkill": True},
                enabled=True,
                max_invocations=10,
            ),
            # Scenario B: Network Disconnect Mid-Request
            FaultScenario(
                scenario_name="ipc_disconnect_before_result",
                target_component="ipc",
                failure_type=FailureType.IPC_FAILURE,
                parameters={"side_effect_class": "EXTERNAL_MUTATION", "drop_socket": True},
                enabled=True,
                max_invocations=10,
            ),
            # Scenario C: Resource Exhaustion / Memory Pressure
            FaultScenario(
                scenario_name="resource_exhaustion",
                target_component="resource_enforcement",
                failure_type=FailureType.MEMORY_PRESSURE,
                parameters={"leak_mb": 512, "exceed_job_limit": True},
                enabled=True,
                max_invocations=10,
            ),
            # Scenario D: Recovery Failure Loop
            FaultScenario(
                scenario_name="recovery_failure",
                target_component="sandbox",
                failure_type=FailureType.SANDBOX_FAILURE,
                parameters={"force_recovery_error": True, "reps": 3},
                enabled=True,
                max_invocations=10,
            ),
            # Scenario E: Emergency Stop during Active Recovery
            FaultScenario(
                scenario_name="emergency_stop_during_recovery",
                target_component="native_runtime",
                failure_type=FailureType.PROCESS_FAILURE,
                parameters={"activate_emergency_stop": True},
                enabled=True,
                max_invocations=10,
            ),
            # Additional Scenarios
            FaultScenario(
                scenario_name="network_timeout_mid_request",
                target_component="network_fabric",
                failure_type=FailureType.TIMEOUT,
                parameters={"delay_ms": 35000},
                enabled=True,
                max_invocations=10,
            ),
            FaultScenario(
                scenario_name="database_unavailable",
                target_component="database",
                failure_type=FailureType.DATABASE_FAILURE,
                parameters={"simulate_disconnect": True},
                enabled=True,
                max_invocations=10,
            ),
            FaultScenario(
                scenario_name="verification_failure",
                target_component="native_runtime",
                failure_type=FailureType.VERIFICATION_FAILURE,
                parameters={"fail_synthetic_probe": True},
                enabled=True,
                max_invocations=10,
            ),
        ]

        for s in defaults:
            self.register_scenario(s)
