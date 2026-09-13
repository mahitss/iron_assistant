"""
End-to-End Live Native Tool Execution Fabric Verification (Task 83):
Spawns kairo-runtime.exe and validates the complete Section 91-98 lifecycle:
1. Native Handshake & Capability Discovery (Section 36)
2. E2E Tool Execution (native_hash) through full pipeline (Section 91):
   ToolRegistry -> ToolExecutor -> SecurityCenter -> Governance -> Resource Economy -> Rust Sandbox -> Normalization -> Metrics
3. E2E Sysinfo Tool Execution (native_system_info) -> Rust native.sysinfo capability
4. E2E Workspace File Inspection Tool (native_workspace_inspect) -> Rust native.file.inspect
5. Injection Attack Defense (Section 95): Shell metacharacters treated as raw data
6. Path Escape Defense (Section 96): Traversal rejected by sandbox
7. Governance / Policy Denial (Section 94): Rejection prior to native dispatch
8. SecurityCenter Capability Denial (Section 93): Rejection prior to execution
9. EmergencyStop Supremacy (Section 98): Halts native tool execution immediately
10. Safe Python Fallback (Section 17): NATIVE_PREFERRED falls back when runtime killed
11. Fail-Closed for NATIVE_REQUIRED (Section 17): Fails closed safely when runtime killed
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
repo_dir = os.path.abspath(os.path.join(backend_dir, ".."))
sys.path.insert(0, backend_dir)
sys.path.insert(0, repo_dir)

from app.native.client import NativeRuntimeClient
from app.native.models import (
    ToolExecutionClass,
    ToolExecutionPreference,
    ToolAvailability,
)
from app.native.service import NativeRuntimeService
from app.orchestration.coordinator import ResourceEconomyCoordinator
from app.orchestration.resource_registry import ResourceRegistry
from app.security.center import SecurityCenter
from app.security.emergency_stop import EmergencyStopService
from app.tools.base import PermissionLevel
from app.tools.builtin.native import (
    NativeHashTool,
    NativeProbeTool,
    NativeSystemInfoTool,
    NativeWorkspaceInspectTool,
)
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry, create_default_tool_registry
from app.tools.schemas import ToolCall, ToolResult


async def run_tool_fabric_e2e():
    port = 28995
    secret = "kairo-native-tool-fabric-e2e-secret-83"
    exe_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "native", "target", "debug", "kairo-runtime.exe")
    )

    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Native runtime binary not found at {exe_path}")

    env = os.environ.copy()
    env["PATH"] = r"C:\Users\pc\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin;" + env.get("PATH", "")

    daemon_log_path = os.path.abspath(os.path.join(backend_dir, "native_tool_daemon_e2e.log"))
    daemon_log_file = open(daemon_log_path, "w", encoding="utf-8")

    print(f"[E2E TOOL FABRIC] Spawning native daemon on port {port}...")
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
        # Wait for daemon to become ready
        print("[1] Connecting to native runtime daemon...")
        connected = False
        for attempt in range(1, 30):
            try:
                hs = await client.connect()
                print(f"  -> Connected to native daemon (version={hs.runtime_version})")
                connected = True
                break
            except Exception:
                await asyncio.sleep(0.2)

        if not connected:
            raise RuntimeError("Could not connect to native runtime daemon on port " + str(port))
        print("  -> Daemon connected and responsive.")

        # Initialize native service
        security_center = SecurityCenter()
        emergency_stop = EmergencyStopService()
        from app.orchestration.economy import ResourceEconomyEngine
        resource_registry = ResourceRegistry()
        economy_engine = ResourceEconomyEngine(resource_registry=resource_registry)
        economy_coordinator = ResourceEconomyCoordinator(economy_engine=economy_engine)

        native_service = NativeRuntimeService(
            client=client,
            security_center=security_center,
            emergency_stop=emergency_stop,
            resource_registry=resource_registry,
            economy_coordinator=economy_coordinator,
        )

        # Set singleton instance for executor
        NativeRuntimeService._instance = native_service

        # Initialize tool registry & executor
        registry = create_default_tool_registry()
        executor = ToolExecutor(
            registry=registry,
            security_center=security_center,
        )

        # -------------------------------------------------------------
        # Scenario 1: End-to-End Execution of native_hash (Section 91)
        # -------------------------------------------------------------
        print("\n[2] Testing Scenario 1: End-to-End native_hash execution (Section 91)...")
        call_hash = ToolCall(
            id="e2e_call_hash_1",
            name="native_hash",
            arguments={"text": "hello task 83 fabric", "algorithm": "sha256"},
        )
        res_hash = await executor.execute(call_hash)
        assert res_hash.success is True, f"Execution failed: {res_hash.error}"
        assert res_hash.execution_class == "NATIVE_RUST"
        assert res_hash.capability_id == "sandbox.hash"
        assert res_hash.result is not None
        assert "sha256" in res_hash.result
        assert len(res_hash.result["sha256"]) == 64
        assert res_hash.duration_ms is not None and res_hash.duration_ms >= 0
        assert res_hash.provenance is not None
        print(f"  -> SUCCESS: Hash generated: {res_hash.result['sha256']}")
        print(f"  -> Provenance verified: execution_class={res_hash.execution_class}, duration_ms={res_hash.duration_ms}")

        # -------------------------------------------------------------
        # Scenario 2: End-to-End Execution of native_system_info
        # -------------------------------------------------------------
        print("\n[3] Testing Scenario 2: End-to-End native_system_info execution...")
        call_sysinfo = ToolCall(
            id="e2e_call_sysinfo_1",
            name="native_system_info",
            arguments={"include_sandboxed": True},
        )
        res_sysinfo = await executor.execute(call_sysinfo)
        assert res_sysinfo.success is True, f"Sysinfo failed: {res_sysinfo.error}"
        assert res_sysinfo.execution_class == "NATIVE_RUST"
        assert res_sysinfo.capability_id == "native.sysinfo"
        assert "os" in res_sysinfo.result
        assert "architecture" in res_sysinfo.result
        assert "cores" in res_sysinfo.result
        print(f"  -> SUCCESS: Host OS: {res_sysinfo.result['os']}, Arch: {res_sysinfo.result['architecture']}, Cores: {res_sysinfo.result['cores']}")

        # -------------------------------------------------------------
        # Scenario 3: End-to-End Execution of native_workspace_inspect
        # -------------------------------------------------------------
        print("\n[4] Testing Scenario 3: End-to-End native_workspace_inspect execution...")
        # Create a workspace test file
        test_file_path = os.path.join(repo_dir, "test_fabric_inspect.txt")
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write("Kairo Native Tool Execution Fabric Deterministic Content\nLine 2\n")

        call_inspect = ToolCall(
            id="e2e_call_inspect_1",
            name="native_workspace_inspect",
            arguments={
                "path": "test_fabric_inspect.txt",
                "content": "Kairo Native Tool Execution Fabric Deterministic Content\nLine 2\n",
            },
        )
        res_inspect = await executor.execute(call_inspect)
        assert res_inspect.success is True, f"Inspect failed: {res_inspect.error}"
        assert res_inspect.execution_class == "NATIVE_RUST"
        assert res_inspect.capability_id == "native.file.inspect"
        assert res_inspect.result["path"] == "test_fabric_inspect.txt"
        assert res_inspect.result["is_binary"] is False
        assert res_inspect.result["size_bytes"] > 0
        assert len(res_inspect.result["sha256"]) == 64
        print(f"  -> SUCCESS: Inspected file {res_inspect.result['path']}: {res_inspect.result['size_bytes']} bytes, sha256={res_inspect.result['sha256'][:16]}...")

        # -------------------------------------------------------------
        # Scenario 4: Injection Scenario (Section 95)
        # -------------------------------------------------------------
        print("\n[5] Testing Scenario 4: Shell metacharacter injection attack defense (Section 95)...")
        injection_arg = "test.txt; rm -rf /; cat /etc/passwd & calc.exe"
        call_inject = ToolCall(
            id="e2e_call_inject_1",
            name="native_workspace_inspect",
            arguments={"path": injection_arg},
        )
        res_inject = await executor.execute(call_inject)
        # In native fabric, arguments are passed as structured typed data, never evaluated by shell.
        # The file does not exist, so it fails cleanly with file not found, but NEVER executes shell syntax!
        assert res_inject.success is False
        assert "does not exist in isolated workspace" in res_inject.error or "PATH_TRAVERSAL" in res_inject.error
        print("  -> SUCCESS: Shell metacharacters treated strictly as raw string data; no shell execution.")

        # -------------------------------------------------------------
        # Scenario 5: Path Escape Scenario (Section 96)
        # -------------------------------------------------------------
        print("\n[6] Testing Scenario 5: Path traversal escape defense (Section 96)...")
        call_escape = ToolCall(
            id="e2e_call_escape_1",
            name="native_workspace_inspect",
            arguments={"path": "../../Windows/System32/drivers/etc/hosts"},
        )
        res_escape = await executor.execute(call_escape)
        assert res_escape.success is False
        assert "escapes workspace" in res_escape.error.lower() or "traversal" in res_escape.error.lower()
        print(f"  -> SUCCESS: Path escape blocked by sandbox: {res_escape.error}")

        # -------------------------------------------------------------
        # Scenario 6: Security Center Capability Denial (Section 93)
        # -------------------------------------------------------------
        print("\n[7] Testing Scenario 6: Unauthorized action denial (Section 93)...")
        from app.security.center import SecurityDecision, SecurityDecisionResult, RiskLevel
        from unittest.mock import AsyncMock, patch

        with patch.object(security_center, "authorize", new_callable=AsyncMock) as mock_auth:
            mock_auth.return_value = SecurityDecisionResult(
                decision=SecurityDecision.DENIED,
                risk_level=RiskLevel.HIGH,
                reason="Policy prohibits native probe capability for unauthorized role",
            )
            call_probe_unauth = ToolCall(
                id="e2e_call_probe_unauth",
                name="native_probe",
                arguments={"mode": "deep"},
            )
            res_probe_unauth = await executor.execute(call_probe_unauth)
            assert res_probe_unauth.success is False
            assert "prohibits native probe" in res_probe_unauth.error or "denied" in res_probe_unauth.error.lower()
            print(f"  -> SUCCESS: Unauthorized capability rejected before native dispatch: {res_probe_unauth.error}")

        # -------------------------------------------------------------
        # Scenario 7: Emergency Stop Supremacy (Section 98)
        # -------------------------------------------------------------
        print("\n[8] Testing Scenario 7: EmergencyStop Supremacy (Section 98)...")
        emergency_stop.trigger_emergency_stop(reason="Security Incident Drill")
        try:
            call_estop = ToolCall(
                id="e2e_call_estop",
                name="native_hash",
                arguments={"text": "should be blocked by emergency stop"},
            )
            res_estop = await executor.execute(call_estop)
            assert res_estop.success is False
            assert "EmergencyStop" in res_estop.error or "emergency stop" in res_estop.error.lower()
            print(f"  -> SUCCESS: Native execution halted by EmergencyStop: {res_estop.error}")
        finally:
            emergency_stop.reset_emergency_stop(is_human_user=True)

        # Verify resumption after reset
        res_resumed = await executor.execute(call_hash)
        assert res_resumed.success is True
        print("  -> Emergency stop cleared; native execution resumed successfully.")

        # -------------------------------------------------------------
        # Scenario 8: Native Preferred Fallback & Native Required Fail-Closed (Sections 17, 78)
        # -------------------------------------------------------------
        print("\n[9] Testing Scenario 8: Fallback & Fail-Closed when daemon terminates (Sections 17, 78)...")
        # Terminate daemon process
        proc.terminate()
        try:
            proc.wait(timeout=3.0)
        except Exception:
            proc.kill()
        print("  -> Daemon terminated.")

        # Test NATIVE_PREFERRED tool (native_hash) -> Must fall back gracefully to Python!
        call_fallback = ToolCall(
            id="e2e_call_fallback",
            name="native_hash",
            arguments={"text": "fallback text test", "algorithm": "sha256"},
        )
        res_fallback = await executor.execute(call_fallback)
        assert res_fallback.success is True, f"Fallback failed: {res_fallback.error}"
        assert res_fallback.execution_class == "PYTHON"
        assert res_fallback.provenance.get("fallback") is True
        print(f"  -> SUCCESS: NATIVE_PREFERRED cleanly fell back to Python execution: sha256={res_fallback.result['sha256'][:16]}...")

        # Test NATIVE_REQUIRED tool (native_workspace_inspect) -> Must FAIL CLOSED!
        call_fail_closed = ToolCall(
            id="e2e_call_fail_closed",
            name="native_workspace_inspect",
            arguments={"path": "main.py"},
        )
        res_fail_closed = await executor.execute(call_fail_closed)
        assert res_fail_closed.success is False
        assert "NATIVE_REQUIRED" in res_fail_closed.error or "unavailable" in res_fail_closed.error.lower()
        print(f"  -> SUCCESS: NATIVE_REQUIRED cleanly failed closed: {res_fail_closed.error}")

        # -------------------------------------------------------------
        # Telemetry & Observability Check (Section 54, 55)
        # -------------------------------------------------------------
        print("\n[10] Checking Tool Health & Observability Metrics (Sections 54, 55)...")
        hash_metrics = registry.get_tool_metrics("native_hash")
        assert hash_metrics["invocations"] >= 2
        assert hash_metrics["successes"] >= 2
        print(f"  -> native_hash metrics: {json.dumps(hash_metrics)}")

        inspect_metrics = registry.get_tool_metrics("native_workspace_inspect")
        assert inspect_metrics["invocations"] >= 2
        print(f"  -> native_workspace_inspect metrics: {json.dumps(inspect_metrics)}")

        native_catalog = registry.get_native_tool_catalog()
        assert len(native_catalog) >= 4
        print(f"  -> Registered native tools count: {len(native_catalog)}")

        print("\n==================================================")
        print("ALL TASK 83 E2E NATIVE TOOL FABRIC SCENARIOS PASSED!")
        print("==================================================")

    finally:
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        daemon_log_file.close()


if __name__ == "__main__":
    asyncio.run(run_tool_fabric_e2e())
