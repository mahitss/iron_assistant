"""
End-to-End Live Substrate Resource Enforcement & Execution Economy Verification (Task 82):
Spawns kairo-runtime.exe and validates the complete Section 101 Scenario:
1. Normal compliant workload:
   - Atomic reservation of CPU, memory, time, output
   - Native execution in isolated workspace
   - Rich telemetry collection (wall_time, peak_memory, process_count, output_bytes)
   - Guaranteed reservation release (zero leaks)
   - Reconciliation of variance & estimation learning
2. Memory limit violation:
   - Workload exceeds memory budget
   - Enforced by OS / runtime limit checks
   - Returns RESOURCE_EXCEEDED with structured ResourceViolation
   - Reservation released without leaks
3. Time limit violation:
   - Workload exceeds deadline
   - Returns TIMED_OUT with TIME_LIMIT_EXCEEDED violation
   - Reservation released without leaks
4. Output limit violation:
   - Workload exceeds stdout bytes
   - Stream truncated, returns RESOURCE_EXCEEDED
   - Reservation released without leaks
5. Disk limit violation:
   - Workload floods files
   - Bounded and returns RESOURCE_EXCEEDED
   - Reservation released without leaks
6. Backpressure & Capacity Exhaustion:
   - Capacity saturated in ResourceRegistry
   - Workload rejected as RESOURCE_UNAVAILABLE
7. EmergencyStop Supremacy:
   - Active EmergencyStop immediately rejects workloads
   - Zero reservation leaks
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
repo_dir = os.path.abspath(os.path.join(backend_dir, ".."))
sys.path.insert(0, backend_dir)
sys.path.insert(0, repo_dir)

from app.native.client import NativeRuntimeClient
from app.native.models import (
    EnforcementAction,
    ErrorCategory,
    ExecutionRequest,
    ExecutionState,
    OutputLimits,
    ResourceBudget,
    ResourceViolationType,
    SandboxPolicy,
    SandboxProfile,
    ViolationSeverity,
)
from app.native.service import NativeRuntimeService
from app.orchestration.coordinator import ResourceEconomyCoordinator
from app.orchestration.economy import ResourceEconomyEngine
from app.orchestration.resource_registry import ResourceRegistry


async def run_resource_economy_e2e():
    port = 28990
    secret = "kairo-resource-economy-e2e-secret-7782"
    exe_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "native", "target", "debug", "kairo-runtime.exe")
    )

    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Native runtime binary not found at {exe_path}")

    env = os.environ.copy()
    env["PATH"] = r"C:\Users\pc\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin;" + env.get("PATH", "")

    daemon_log_path = os.path.abspath(os.path.join(backend_dir, "native_economy_daemon_e2e.log"))
    daemon_log_file = open(daemon_log_path, "w", encoding="utf-8")

    print(f"[E2E ECONOMY] Spawning native daemon on port {port}...")
    proc = subprocess.Popen(
        [exe_path, "--port", str(port), "--secret", secret, "--log-level", "debug"],
        env=env,
        stdout=daemon_log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )

    client = NativeRuntimeClient(
        host="127.0.0.1",
        port=port,
        secret=secret,
        timeout_seconds=10.0,
    )

    try:
        # 1. Connect & Handshake
        connected = False
        for attempt in range(1, 30):
            try:
                hs = await client.connect()
                print(f"[E2E ECONOMY] Connected to native substrate daemon (version={hs.runtime_version})")
                connected = True
                break
            except Exception:
                await asyncio.sleep(0.2)

        if not connected:
            raise RuntimeError("Failed to connect to native substrate daemon after 30 attempts")

        # 2. Setup Service with real ResourceRegistry and Economy Coordinator
        registry = ResourceRegistry()
        economy_engine = ResourceEconomyEngine(resource_registry=registry)
        coordinator = ResourceEconomyCoordinator(economy_engine=economy_engine)

        service = NativeRuntimeService(
            client=client,
            resource_registry=registry,
            economy_coordinator=coordinator,
        )
        service.mode = "REQUIRED"

        # Check initial economy status
        status = service.get_resource_economy_status()
        print(f"[E2E ECONOMY] Initial Resource Status: Saturation={status['saturation_pct']}%, State={status['saturation_state']}")
        mem_res = registry.get("native_memory")
        initial_capacity = mem_res.available_capacity

        # =====================================================================
        # SCENARIO 1: Compliant Workload with Complete Telemetry & Learning
        # =====================================================================
        print("\n--- SCENARIO 1: Compliant Execution & Estimation Learning ---")
        req1 = ExecutionRequest(
            request_id="req-e2e-eco-1",
            capability_id="sandbox.echo",
            arguments=["Kairo Native Resource Economy Live Test"],
            resource_budget=ResourceBudget(
                max_memory_bytes=256 * 1024 * 1024, # 256 MiB
                max_execution_time_ms=10000,
            ),
        )

        res1 = await service.sandbox_execute(req1)
        assert res1.state == ExecutionState.COMPLETED, f"Expected COMPLETED, got {res1.state}: {res1.stderr}"
        assert "Kairo Native Resource Economy Live Test" in res1.stdout
        assert res1.resource_telemetry is not None, "Missing resource telemetry in ExecutionResult"
        telem = res1.resource_telemetry
        print(f"[E2E ECONOMY] Telemetry: WallTime={telem.wall_time_ms}ms, PeakMemory={telem.peak_memory_bytes} bytes, Output={telem.output_bytes} bytes, Quality={telem.measurement_quality.value}")
        assert telem.wall_time_ms >= 0
        assert res1.resource_violation is None, "Expected no violations on compliant workload"

        # Verify zero reservation leak
        assert mem_res.available_capacity == initial_capacity, f"Reservation leaked! Available={mem_res.available_capacity}, initial={initial_capacity}"
        print(f"[E2E ECONOMY] Clean Release Verified: Available memory restored to {mem_res.available_capacity} MB")

        # Verify learning
        assert "native:sandbox.echo" in coordinator.economy._historical_demands, "Estimation learning sample missing"
        print(f"[E2E ECONOMY] Estimation Learning Updated: {coordinator.economy._historical_demands['native:sandbox.echo']}")

        # =====================================================================
        # SCENARIO 2: Memory Limit Exceeded Violation
        # =====================================================================
        print("\n--- SCENARIO 2: Memory Limit Exceeded Enforcement ---")
        req2 = ExecutionRequest(
            request_id="req-e2e-eco-2",
            capability_id="sandbox.probe",
            payload={
                "mode": "memory_burn",
                "megabytes": 128,
            },
            sandbox_policy=SandboxPolicy(
                resource_budget=ResourceBudget(
                    max_memory_bytes=64 * 1024 * 1024, # 64 MiB limit vs 128 MiB requested
                ),
            ),
        )

        res2 = await service.sandbox_execute(req2)
        assert res2.state == ExecutionState.RESOURCE_EXCEEDED, f"Expected RESOURCE_EXCEEDED, got {res2.state}"
        assert res2.resource_violation is not None, "Missing resource_violation struct"
        assert res2.resource_violation.violation_type == ResourceViolationType.MEMORY_LIMIT_EXCEEDED
        assert res2.resource_violation.severity == ViolationSeverity.HARD_LIMIT
        assert res2.resource_violation.enforcement_action == EnforcementAction.TERMINATE
        print(f"[E2E ECONOMY] Hard Memory Violation Detected: {res2.resource_violation.message}")

        # Verify zero reservation leak after violation
        assert mem_res.available_capacity == initial_capacity, "Reservation leaked after memory violation!"
        print(f"[E2E ECONOMY] Clean Release After Violation Verified: {mem_res.available_capacity} MB available")

        # =====================================================================
        # SCENARIO 3: Wall-clock Time Limit Exceeded
        # =====================================================================
        print("\n--- SCENARIO 3: Wall-Clock Deadline Enforcement ---")
        req3 = ExecutionRequest(
            request_id="req-e2e-eco-3",
            capability_id="sandbox.probe",
            payload={
                "mode": "sleep",
                "duration_ms": 2000,
            },
            sandbox_policy=SandboxPolicy(
                resource_budget=ResourceBudget(
                    max_execution_time_ms=100, # 100ms deadline vs 2000ms sleep
                ),
            ),
        )

        res3 = await service.sandbox_execute(req3)
        assert res3.state == ExecutionState.TIMED_OUT, f"Expected TIMED_OUT, got {res3.state}"
        assert res3.timeout_state is True
        assert res3.resource_violation is not None
        assert res3.resource_violation.violation_type == ResourceViolationType.TIME_LIMIT_EXCEEDED
        print(f"[E2E ECONOMY] Timeout Violation Detected: {res3.resource_violation.message}")
        assert mem_res.available_capacity == initial_capacity, "Reservation leaked after timeout!"

        # =====================================================================
        # SCENARIO 4: Output Limit Exceeded
        # =====================================================================
        print("\n--- SCENARIO 4: Output Bounding Enforcement ---")
        req4 = ExecutionRequest(
            request_id="req-e2e-eco-4",
            capability_id="sandbox.probe",
            payload={"mode": "flood"},
            sandbox_policy=SandboxPolicy(
                output_limits=OutputLimits(
                    max_stdout_bytes=1024,
                    max_stderr_bytes=1024,
                    max_combined_bytes=2048,
                ),
            ),
        )

        res4 = await service.sandbox_execute(req4)
        assert res4.state == ExecutionState.RESOURCE_EXCEEDED
        assert res4.output_metadata.truncated is True
        print(f"[E2E ECONOMY] Output Bounded & Truncated at {res4.output_metadata.stdout_bytes} bytes")
        assert mem_res.available_capacity == initial_capacity, "Reservation leaked after output flood!"

        # =====================================================================
        # SCENARIO 5: Disk Flood & File Count Enforcement
        # =====================================================================
        print("\n--- SCENARIO 5: Workspace Storage Limits ---")
        req5 = ExecutionRequest(
            request_id="req-e2e-eco-5",
            capability_id="sandbox.probe",
            payload={
                "mode": "disk_flood",
                "file_count": 20,
                "bytes_per_file": 100,
            },
            sandbox_policy=SandboxPolicy(
                resource_budget=ResourceBudget(
                    max_file_count=5, # only 5 files allowed
                ),
            ),
        )

        res5 = await service.sandbox_execute(req5)
        assert res5.state == ExecutionState.RESOURCE_EXCEEDED
        assert res5.resource_violation is not None
        assert res5.resource_violation.violation_type == ResourceViolationType.FILE_COUNT_LIMIT_EXCEEDED
        print(f"[E2E ECONOMY] Workspace File Count Violation Detected: {res5.resource_violation.message}")
        assert mem_res.available_capacity == initial_capacity, "Reservation leaked after disk flood!"

        # =====================================================================
        # SCENARIO 6: Backpressure & Resource Contention
        # =====================================================================
        print("\n--- SCENARIO 6: Backpressure & Capacity Exhaustion ---")
        # Artificially squeeze available capacity
        mem_res.available_capacity = 20.0 # only 20 MB

        req6 = ExecutionRequest(
            request_id="req-e2e-eco-6",
            capability_id="sandbox.echo",
            resource_budget=ResourceBudget(max_memory_bytes=512 * 1024 * 1024), # 512 MB requested
        )

        res6 = await service.sandbox_execute(req6)
        assert res6.state == ExecutionState.REJECTED
        assert res6.failure_classification == "RESOURCE_UNAVAILABLE"
        print(f"[E2E ECONOMY] Backpressure Engaged: {res6.stderr}")

        # Restore capacity
        mem_res.available_capacity = initial_capacity

        # =====================================================================
        # SCENARIO 7: EmergencyStop Supremacy Overriding Scheduling
        # =====================================================================
        print("\n--- SCENARIO 7: EmergencyStop Invariant ---")
        service.emergency_stop.trigger_emergency_stop(reason="Global security containment")
        try:
            req7 = ExecutionRequest(
                request_id="req-e2e-eco-7",
                capability_id="sandbox.echo",
            )
            res7 = await service.sandbox_execute(req7)
            assert res7.state == ExecutionState.REJECTED
            assert res7.failure_classification == "EMERGENCY_STOP_ACTIVE"
            assert res7.error.category == ErrorCategory.AUTHORIZATION_REQUIRED
            print("[E2E ECONOMY] EmergencyStop Halted Execution Instantly: Zero Resource Leakage")
            assert mem_res.available_capacity == initial_capacity
        finally:
            service.emergency_stop.reset_emergency_stop(is_human_user=True)

        print("\n=======================================================")
        print(" [E2E ECONOMY] ALL 7 REAL-TIME SCENARIOS PASSED WITH ZERO LEAKS!")
        print("=======================================================\n")

    finally:
        print("[E2E ECONOMY] Terminating daemon process...")
        try:
            await client.disconnect()
        except Exception:
            pass
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            proc.kill()
        daemon_log_file.close()


if __name__ == "__main__":
    asyncio.run(run_resource_economy_e2e())
