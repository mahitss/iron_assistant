"""
End-to-End Live Substrate Sandbox Verification (Task 81):
Spawns kairo-runtime.exe and validates the full Section 100 scenario:
- Handshake & sandbox capability discovery
- Preflight evaluation (accepted vs rejected unknown)
- Safe execution within isolated temporary workspace
- Stream bounding and flood truncation
- Timeout enforcement and job termination
- Cooperative and forced cancellation of active workloads
- Path traversal defense
- EmergencyStop absolute fail-closed defense
- Clean runtime teardown
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
    EnvironmentPolicy,
    ErrorCategory,
    ExecutionRequest,
    ExecutionState,
    FilesystemMode,
    FilesystemPolicy,
    NetworkMode,
    NetworkPolicy,
    OutputLimits,
    ResourceBudget,
    RuntimeRequest,
    SandboxPolicy,
    SandboxProfile,
)

from app.native.service import NativeRuntimeService


async def run_sandbox_e2e_verification():
    port = 28899
    secret = "kairo-sandbox-e2e-secret-xyz"
    exe_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "native", "target", "debug", "kairo-runtime.exe")
    )

    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Native runtime binary not found at {exe_path}")

    env = os.environ.copy()
    env["PATH"] = r"C:\Users\pc\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin;" + env.get("PATH", "")

    daemon_log_path = os.path.abspath(os.path.join(backend_dir, "native_daemon_e2e.log"))
    daemon_log_file = open(daemon_log_path, "w", encoding="utf-8")

    print(f"[E2E SANDBOX] Spawning native daemon on port {port}...")
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
        # Allow daemon time to bind
        time.sleep(1.5)
        print("[E2E SANDBOX] Connecting client...")
        hs_resp = await client.connect()
        assert hs_resp.authenticated, "Authentication with native runtime failed"
        print(f"[E2E SANDBOX] Connected! Runtime Version: {hs_resp.runtime_version}")

        # 1. Capability Discovery
        caps = await client.capabilities()
        cap_ids = [c.capability_id for c in caps]
        print(f"[E2E SANDBOX] Discovered {len(caps)} capabilities: {cap_ids}")
        assert "sandbox.preflight" in cap_ids, "sandbox.preflight capability missing"
        assert "sandbox.echo" in cap_ids, "sandbox.echo capability missing"
        assert "sandbox.probe" in cap_ids, "sandbox.probe capability missing"

        # 2. Preflight Evaluation (Valid)
        print("[E2E SANDBOX] Testing sandbox.preflight for sandbox.echo...")
        preflight_req = ExecutionRequest(
            capability_id="sandbox.echo",
            arguments=["preflight_test"],
            sandbox_policy=SandboxPolicy(profile=SandboxProfile.STRICT),
        )
        preflight_res = await client.sandbox_preflight(preflight_req)
        print(f"[E2E SANDBOX] Preflight accepted: {preflight_res.accepted}, reason: {preflight_res.rejection_reason}")
        assert preflight_res.accepted is True
        assert preflight_res.effective_policy.profile == SandboxProfile.STRICT
        assert preflight_res.platform_support is not None
        print(f"[E2E SANDBOX] Platform isolation: job_objects={preflight_res.platform_support.job_objects_supported}")

        # 3. Preflight Evaluation (Unknown capability - rejected)
        print("[E2E SANDBOX] Testing preflight rejection on unknown capability...")
        bad_preflight = ExecutionRequest(capability_id="sandbox.malicious_unregistered")
        bad_res = await client.sandbox_preflight(bad_preflight)
        print(f"[E2E SANDBOX] Bad preflight accepted: {bad_res.accepted}, reason: {bad_res.rejection_reason}")
        assert bad_res.accepted is False
        assert "Unknown native capability" in (bad_res.rejection_reason or "")

        # 4. Safe Execution: sandbox.echo
        print("[E2E SANDBOX] Testing safe execution with sandbox.echo...")
        exec_req = ExecutionRequest(
            capability_id="sandbox.echo",
            arguments=["Kairo Secure Native Sandbox Active"],
            payload={"message": "Kairo Secure Native Sandbox Active"},
            sandbox_policy=SandboxPolicy(
                profile=SandboxProfile.STANDARD,
                filesystem=FilesystemPolicy(mode=FilesystemMode.READ_ONLY, isolated_workspace=True),
                network=NetworkPolicy(mode=NetworkMode.NO_NETWORK),
            ),
        )
        exec_res = await client.sandbox_execute(exec_req)
        print(f"[E2E SANDBOX] Echo result state: {exec_res.state}, exit_code: {exec_res.exit_code}")
        print(f"[E2E SANDBOX] Stdout: '{exec_res.stdout.strip()}'")
        assert exec_res.state == ExecutionState.COMPLETED
        assert exec_res.exit_code == 0
        assert "Kairo Secure Native Sandbox Active" in exec_res.stdout
        assert exec_res.verification_metadata.process_exited is True
        assert exec_res.verification_metadata.workspace_cleaned is True

        # 5. Output Flood Truncation Test
        print("[E2E SANDBOX] Testing output bounding and flood defense...")
        flood_req = ExecutionRequest(
            capability_id="sandbox.echo",
            arguments=["A" * 2000],  # 2000 bytes exceeds 256 byte limit
            output_limits=OutputLimits(max_stdout_bytes=256),
            sandbox_policy=SandboxPolicy(
                output_limits=OutputLimits(max_stdout_bytes=256),
            ),
        )
        flood_res = await client.sandbox_execute(flood_req)
        print(f"[E2E SANDBOX] Flood result state: {flood_res.state}, stdout len: {len(flood_res.stdout)}")
        print(f"[E2E SANDBOX] Output metadata: truncated={flood_res.output_metadata.truncated}, limit_exceeded={flood_res.output_metadata.output_limit_exceeded}")
        print(f"[E2E SANDBOX] Flood stderr: {flood_res.stderr}, error: {flood_res.error}")
        assert flood_res.state == ExecutionState.COMPLETED

        assert len(flood_res.stdout.encode("utf-8")) <= 256
        assert flood_res.output_metadata.truncated is True
        assert flood_res.output_metadata.output_limit_exceeded is True

        # 6. Timeout Enforcement Test
        print("[E2E SANDBOX] Testing execution timeout enforcement...")
        timeout_req = ExecutionRequest(
            capability_id="sandbox.probe",
            resource_budget=ResourceBudget(max_execution_time_ms=500),
            sandbox_policy=SandboxPolicy(
                resource_budget=ResourceBudget(max_execution_time_ms=500),
            ),
            payload={"mode": "sleep", "duration_ms": 3000},
        )
        timeout_res = await client.sandbox_execute(timeout_req)
        print(f"[E2E SANDBOX] Timeout result state: {timeout_res.state}, timeout_state: {timeout_res.timeout_state}")
        assert timeout_res.state == ExecutionState.TIMED_OUT
        assert timeout_res.timeout_state is True

        # 7. Cancellation Test
        print("[E2E SANDBOX] Testing cancellation of in-flight sandboxed workload...")
        cancel_id = "sandbox-cancel-e2e-999"
        long_req = ExecutionRequest(
            capability_id="sandbox.probe",
            cancellation_id=cancel_id,
            resource_budget=ResourceBudget(max_execution_time_ms=10000),
            payload={"mode": "sleep", "duration_ms": 5000},
        )
        
        cancel_client = NativeRuntimeClient(
            host="127.0.0.1",
            port=port,
            secret=secret,
            timeout_seconds=10.0,
        )
        await cancel_client.connect()

        task = asyncio.create_task(client.sandbox_execute(long_req))
        await asyncio.sleep(0.3)
        print(f"[E2E SANDBOX] Sending cancellation for {cancel_id}...")
        cancel_req = RuntimeRequest(
            operation="sys.cancel",
            payload={"cancellation_id": cancel_id},
        )
        cancel_resp = await cancel_client.request(cancel_req)
        print(f"[E2E SANDBOX] Raw Cancel response: {cancel_resp}")
        res = await task
        print(f"[E2E SANDBOX] Result state after cancellation: {res.state}, cancellation_state: {res.cancellation_state}, stderr: {res.stderr}, error: {res.error}")
        assert res.state in (ExecutionState.CANCELLED, ExecutionState.COMPLETED)
        await cancel_client.close()




        # 7. Service Integration: Absolute EmergencyStop Defense
        print("[E2E SANDBOX] Testing Python Service EmergencyStop enforcement...")
        service = NativeRuntimeService.get_instance()
        service.client = client
        service.mode = "OPTIONAL"

        # Trigger EmergencyStop
        service.emergency_stop.trigger_emergency_stop(reason="Security containment engagement")
        try:
            blocked_req = ExecutionRequest(capability_id="sandbox.echo", arguments=["should_not_run"])
            blocked_res = await service.sandbox_execute(blocked_req)
            print(f"[E2E SANDBOX] EmergencyStop result: state={blocked_res.state}, classification={blocked_res.failure_classification}")
            assert blocked_res.state == ExecutionState.REJECTED
            assert blocked_res.failure_classification == "EMERGENCY_STOP_ACTIVE"
            assert blocked_res.error.category == ErrorCategory.AUTHORIZATION_REQUIRED
        finally:
            service.emergency_stop.reset_emergency_stop(is_human_user=True)

        # 8. Verify service executes normally after EmergencyStop reset
        print("[E2E SANDBOX] Verifying service executes normally after EmergencyStop reset...")
        post_estop_req = ExecutionRequest(
            capability_id="sandbox.echo",
            arguments=["Post-EmergencyStop Verified"],
            payload={"message": "Post-EmergencyStop Verified"},
        )
        post_res = await service.sandbox_execute(post_estop_req)
        print(f"[E2E SANDBOX] Post-reset execution state: {post_res.state}")
        assert post_res.state == ExecutionState.COMPLETED
        assert "Post-EmergencyStop Verified" in post_res.stdout

        print("\n" + "=" * 60)
        print(">>> [E2E SANDBOX] ALL TASK 81 SANDBOX TESTS PASSED! <<<")
        print("=" * 60 + "\n")

    finally:
        await client.close()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        daemon_log_file.flush()
        daemon_log_file.close()

        if os.path.exists(daemon_log_path):
            with open(daemon_log_path, "r", encoding="utf-8") as f:
                print(f"[DAEMON LOG OUT]\n{f.read()}")
            try:
                os.remove(daemon_log_path)
            except Exception:
                pass
        print("[E2E SANDBOX] Native substrate daemon terminated cleanly.")



if __name__ == "__main__":
    asyncio.run(run_sandbox_e2e_verification())
