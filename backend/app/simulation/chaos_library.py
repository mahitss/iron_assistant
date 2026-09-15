"""Chaos Scenario Library & Resilience Injection Engine (Task 89).

Provides 14 canonical pre-configured chaos drill scenarios for resilience testing:
1. `chaos_crash_native_daemon`: Sudden unannounced exit of native runtime daemon.
2. `chaos_ipc_socket_disconnect`: Simulated transport disconnection / pipe severed.
3. `chaos_memory_leak_pressure`: Memory RSS spike to 95% threshold.
4. `chaos_cpu_exhaustion_spin`: CPU saturation causing scheduling latency.
5. `chaos_corrupt_sandbox`: Host sandbox environment corruption.
6. `chaos_stale_connection_pool`: Socket pool starvation / hung keep-alive.
7. `chaos_network_packet_loss`: High packet loss / timeout on external requests.
8. `chaos_database_contention`: High concurrency write lock contention.
9. `chaos_zombie_process_accumulation`: Unreaped child workers leaking handles.
10. `chaos_emergency_stop_trip`: Emergency stop engaged under load.
11. `chaos_workflow_step_failure`: Critical pipeline step exception with dependencies.
12. `chaos_authorization_expiry`: Request token expiring mid-execution.
13. `chaos_toctou_mutation`: Concurrent modification of target resource.
14. `chaos_cascading_subsystem_outage`: Compound multi-failure scenario.

Safety Invariant:
All chaos scenarios execute STRICTLY within digital twin simulation mode with
simulated mutation blocks and zero real-world side effects.
"""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any

from app.simulation.digital_twin import RuntimeSnapshot
from app.simulation.recovery_models import RecoveryScenario, SimulationMode

logger = logging.getLogger("kairo.simulation.chaos_library")


CHAOS_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "chaos_crash_native_daemon",
        "name": "Native Runtime Daemon Crash",
        "subsystem": "native_runtime",
        "description": "Simulate sudden unexpected exit (SIGKILL / panic) of native Rust runner.",
        "hypothesis": "Recovery engine selects RESTART_COMPONENT and reconciles orphan states within 3.5s.",
        "mode": SimulationMode.FAULT_INJECTION,
        "actions": [{"type": "FORCE_CRASH", "target": "native_runtime_daemon"}],
        "state_delta": {"runtime": {"status": "STOPPED"}},
    },
    {
        "id": "chaos_ipc_socket_disconnect",
        "name": "IPC Transport Socket Severance",
        "subsystem": "native_runtime",
        "description": "Simulate broken named pipe / IPC stream during active mutating operation.",
        "hypothesis": "Client identifies UNKNOWN_OUTCOME and executes idempotent RECONNECT.",
        "mode": SimulationMode.FAULT_INJECTION,
        "actions": [{"type": "SEVER_PIPE", "target": "ipc_transport"}],
        "state_delta": {"runtime": {"status": "DEGRADED"}},
    },
    {
        "id": "chaos_memory_leak_pressure",
        "name": "Memory RSS Exhaustion Spike",
        "subsystem": "resource",
        "description": "Simulate unbounded memory consumption climbing above 90% threshold.",
        "hypothesis": "Engine executes RELEASE_LEAKED_RESOURCE and forces garbage collection.",
        "mode": SimulationMode.RESOURCE_SIMULATION,
        "actions": [{"type": "CONSUME_MEMORY", "target_mb": 1024}],
        "state_delta": {"compute": {"memory_pressure_pct": 92.5, "memory_rss_mb": 950.0}},
    },
    {
        "id": "chaos_cpu_exhaustion_spin",
        "name": "CPU Saturation & Starvation",
        "subsystem": "resource",
        "description": "Simulate worker thread lockup saturating available CPU cores.",
        "hypothesis": "Engine throttles background jobs and applies DEGRADE_CAPABILITY.",
        "mode": SimulationMode.RESOURCE_SIMULATION,
        "actions": [{"type": "CPU_SPIN", "duration_ms": 3000}],
        "state_delta": {"compute": {"cpu_pressure_pct": 98.0, "cpu_usage_pct": 95.0}},
    },
    {
        "id": "chaos_corrupt_sandbox",
        "name": "Host Sandbox Container Corruption",
        "subsystem": "sandbox",
        "description": "Simulate sandbox root filesystem corruption and process jail escape attempt.",
        "hypothesis": "Engine executes RECREATE_SANDBOX, tearing down jail and isolating ephemeral storage.",
        "mode": SimulationMode.FAULT_INJECTION,
        "actions": [{"type": "CORRUPT_FILESYSTEM", "target": "sandbox_root"}],
        "state_delta": {"compute": {"sandbox_state": "CORRUPTED"}},
    },
    {
        "id": "chaos_stale_connection_pool",
        "name": "Socket Pool Poisoning & Starvation",
        "subsystem": "network",
        "description": "Simulate hung remote HTTP endpoints holding connections open indefinitely.",
        "hypothesis": "Engine executes REBUILD_CONNECTION_POOL and drains poisoned connections.",
        "mode": SimulationMode.DISCRETE_EVENT,
        "actions": [{"type": "EXHAUST_POOL", "sockets": 50}],
        "state_delta": {"network": {"pool_available": 0, "pool_in_use": 10}},
    },
    {
        "id": "chaos_network_packet_loss",
        "name": "Network Packet Loss & Timeout Storm",
        "subsystem": "network",
        "description": "Simulate 40% packet drop rate across external API gateways.",
        "hypothesis": "Engine trips circuit breaker and falls back to cached responses.",
        "mode": SimulationMode.FAULT_INJECTION,
        "actions": [{"type": "DROP_PACKETS", "loss_pct": 40.0}],
        "state_delta": {"network": {"network_health": "DEGRADED", "circuit_breaker_state": "OPEN"}},
    },
    {
        "id": "chaos_database_contention",
        "name": "Transactional Lock Contention",
        "subsystem": "database",
        "description": "Simulate database table lock contention delaying state persistence.",
        "hypothesis": "Engine executes bounded RETRY with exponential backoff and jitter.",
        "mode": SimulationMode.DISCRETE_EVENT,
        "actions": [{"type": "LOCK_CONTENTION", "table": "workflows"}],
        "state_delta": {"workflows": {"failed_steps_count": 2}},
    },
    {
        "id": "chaos_zombie_process_accumulation",
        "name": "Zombie Process & Handle Leak",
        "subsystem": "resource",
        "description": "Simulate un-reaped subprocesses accumulating hundreds of OS handles.",
        "hypothesis": "Engine executes RESTART_PROCESS and reaps orphaned PID trees.",
        "mode": SimulationMode.RESOURCE_SIMULATION,
        "actions": [{"type": "LEAK_HANDLES", "count": 2000}],
        "state_delta": {"compute": {"handles_count": 2400}},
    },
    {
        "id": "chaos_emergency_stop_trip",
        "name": "Security Emergency Stop Engagement",
        "subsystem": "security",
        "description": "Simulate administrative safety trip halting all execution pipelines.",
        "hypothesis": "Engine preempts all in-flight simulations, drains work, and rejects new jobs.",
        "mode": SimulationMode.FAULT_INJECTION,
        "actions": [{"type": "TRIP_EMERGENCY_STOP", "scope": "system"}],
        "state_delta": {"security": {"emergency_stop_active": True}},
    },
    {
        "id": "chaos_workflow_step_failure",
        "name": "Workflow Pipeline Dependency Failure",
        "subsystem": "workflow",
        "description": "Simulate critical workflow step crash with cascading downstream dependencies.",
        "hypothesis": "Engine isolates failure, executes PAUSE_WORKFLOW, and alerts orchestrator.",
        "mode": SimulationMode.DISCRETE_EVENT,
        "actions": [{"type": "FAIL_STEP", "step_id": "step_compute_matrix"}],
        "state_delta": {"workflows": {"paused_runs_count": 1, "failed_steps_count": 1}},
    },
    {
        "id": "chaos_authorization_expiry",
        "name": "Mid-Execution Token Expiration",
        "subsystem": "security",
        "description": "Simulate security credentials expiring midway through sensitive execution.",
        "hypothesis": "Engine blocks unauthorized mutations and initiates re-authentication flow.",
        "mode": SimulationMode.FAULT_INJECTION,
        "actions": [{"type": "EXPIRE_TOKEN", "subject": "admin_worker"}],
        "state_delta": {"security": {"pending_approvals_count": 1}},
    },
    {
        "id": "chaos_toctou_mutation",
        "name": "Concurrent TOCTOU Resource Mutation",
        "subsystem": "system",
        "description": "Simulate resource hash change between validation and native execution.",
        "hypothesis": "TargetContext revalidation rejects execution with TARGET_CHANGED error.",
        "mode": SimulationMode.DISCRETE_EVENT,
        "actions": [{"type": "MUTATE_TARGET", "resource_id": "res_shared_cfg"}],
        "state_delta": {"tools": {"recent_failures_count": 1}},
    },
    {
        "id": "chaos_cascading_subsystem_outage",
        "name": "Cascading Multi-Subsystem Outage",
        "subsystem": "system",
        "description": "Simulate simultaneous network degradation, memory pressure, and daemon stall.",
        "hypothesis": "Engine prioritizes containment, isolates blast radius, and executes coordinated ladder.",
        "mode": SimulationMode.FAULT_INJECTION,
        "actions": [
            {"type": "SEVER_PIPE", "target": "ipc_transport"},
            {"type": "CONSUME_MEMORY", "target_mb": 800},
            {"type": "DROP_PACKETS", "loss_pct": 50.0},
        ],
        "state_delta": {
            "runtime": {"status": "DEGRADED"},
            "compute": {"memory_pressure_pct": 88.0},
            "network": {"network_health": "DEGRADED"},
        },
    },
]


class ChaosScenarioLibrary:
    """Manages the catalog of pre-configured chaos drill scenarios."""

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Returns catalog of all 14 chaos scenarios."""
        return copy.deepcopy(CHAOS_DEFINITIONS)

    def get_scenario_definition(self, scenario_id: str) -> dict[str, Any] | None:
        """Looks up chaos definition by unique identifier."""
        for sc in CHAOS_DEFINITIONS:
            if sc["id"] == scenario_id:
                return copy.deepcopy(sc)
        return None

    def build_recovery_scenario(
        self,
        scenario_id: str,
        base_snapshot: RuntimeSnapshot,
    ) -> tuple[RecoveryScenario, RuntimeSnapshot]:
        """Creates a typed RecoveryScenario and perturbed clone snapshot for simulation."""
        defn = self.get_scenario_definition(scenario_id)
        if not defn:
            raise ValueError(f"Unknown chaos scenario id: {scenario_id}")

        # Clone and perturb snapshot state to represent fault condition
        perturbed_snapshot = copy.deepcopy(base_snapshot)
        perturbed_snapshot.snapshot_id = f"snap_chaos_{uuid.uuid4().hex[:10]}"

        delta = defn.get("state_delta", {})
        if "runtime" in delta:
            perturbed_snapshot.health_state.update(delta["runtime"])
        if "compute" in delta:
            perturbed_snapshot.resource_state.update(delta["compute"])
        if "network" in delta:
            perturbed_snapshot.network_state.update(delta["network"])
        if "security" in delta:
            perturbed_snapshot.security_state.update(delta["security"])
        if "workflows" in delta:
            perturbed_snapshot.workflow_state.update(delta["workflows"])

        # Re-compute hash
        perturbed_snapshot.hash_sha256 = perturbed_snapshot.compute_fingerprint()

        scenario = RecoveryScenario(
            scenario_id=f"scen_{scenario_id}_{uuid.uuid4().hex[:8]}",
            base_snapshot_id=perturbed_snapshot.snapshot_id,
            description=defn["description"],
            hypothesis=defn["hypothesis"],
            target_subsystem=defn["subsystem"],
            actions=defn["actions"],
            assumptions=[
                "Chaos drill executes strictly in sandboxed digital twin simulation.",
                "Real-world production state and hardware are untouched.",
            ],
            simulation_mode=defn["mode"],
        )

        return scenario, perturbed_snapshot


_global_chaos_library = ChaosScenarioLibrary()


def get_chaos_library() -> ChaosScenarioLibrary:
    return _global_chaos_library
