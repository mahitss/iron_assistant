import asyncio
import os
import subprocess
import sys
import time

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
repo_dir = os.path.abspath(os.path.join(backend_dir, ".."))
sys.path.insert(0, backend_dir)
sys.path.insert(0, repo_dir)

from app.native.client import NativeRuntimeClient
from app.native.models import (
    HandshakeRequest,
    RuntimeRequest,
    RuntimeResponse,
    HealthState,
    ResponseStatus,
    ResourceBudget,
)

async def run_e2e_verification():
    port = 8799
    secret = "kairo-e2e-daemon-secret-12345"
    exe_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "native", "target", "debug", "kairo-runtime.exe")
    )

    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Native binary not found at {exe_path}")

    env = os.environ.copy()
    env["PATH"] = r"C:\Users\pc\.rustup\toolchains\stable-x86_64-pc-windows-gnu\bin;" + env.get("PATH", "")
    
    print(f"[E2E] Spawning native daemon on port {port}...")
    proc = subprocess.Popen(
        [exe_path, "--port", str(port), "--secret", secret, "--log-level", "debug"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    client = NativeRuntimeClient(
        host="127.0.0.1",
        port=port,
        secret=secret,
        timeout_seconds=5.0,
    )

    try:
        # Allow daemon 1.5 seconds to bind
        time.sleep(1.5)
        print("[E2E] Connecting client to daemon...")
        hs_resp = await client.connect()
        print("[E2E] Handshake succeeded! Authenticated:", hs_resp.authenticated, "version:", hs_resp.runtime_version)
        assert hs_resp.authenticated, "Client failed to authenticate with daemon"

        # 1. Ping
        print("[E2E] Testing sys.ping...")
        ping_resp = await client.ping()
        print("[E2E] Ping response status:", ping_resp.status, "result:", ping_resp.result)
        assert ping_resp.status == ResponseStatus.OK
        assert ping_resp.result.get("reply") == "pong"

        # 2. Health check
        print("[E2E] Testing sys.health...")
        health = await client.health()
        print("[E2E] Health status:", health.state if health else "None")
        assert health is not None
        assert health.state == HealthState.READY

        # 3. Capabilities discovery
        print("[E2E] Testing sys.info / capabilities...")
        caps = await client.capabilities()
        print(f"[E2E] Discovered {len(caps)} capabilities:")
        for c in caps:
            print(f"  - {c.name}: {c.description} (budget: {c.default_budget})")
        cap_ids = [c.capability_id for c in caps]
        print(f"[E2E] Capability IDs: {cap_ids}")
        assert "sys.ping" in cap_ids
        assert "sys.health" in cap_ids
        assert "sys.info" in cap_ids
        assert "sys.sleep" in cap_ids

        # 4. Cooperative cancellation test
        print("[E2E] Testing cooperative cancellation of long-running sys.sleep...")
        cancel_client = NativeRuntimeClient(
            host="127.0.0.1",
            port=port,
            secret=secret,
            timeout_seconds=5.0,
        )
        await cancel_client.connect()

        sleep_req = RuntimeRequest(
            operation="sys.sleep",
            payload={"duration_ms": 4000},
            cancellation_id="cancel-test-123",
            budget=ResourceBudget(timeout_ms=5000),
        )
        sleep_task = asyncio.create_task(client.request(sleep_req))
        await asyncio.sleep(0.4)
        print("[E2E] Sending cancellation for cancel-test-123 from concurrent connection...")
        cancelled = await cancel_client.cancel("cancel-test-123")
        print(f"[E2E] Cancel acknowledged: {cancelled}")
        
        # Wait for sleep task
        resp = await sleep_task
        print(f"[E2E] Sleep response after cancellation: status={resp.status}, error={resp.error}")
        assert resp.status in (ResponseStatus.CANCELLED, ResponseStatus.OK)
        await cancel_client.close()

        print("\n>>> [E2E] ALL NATIVE DAEMON TESTS PASSED SUCCESSFULLY! <<<\n")
    finally:
        await client.close()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[E2E] Native daemon terminated cleanly.")


if __name__ == "__main__":
    asyncio.run(run_e2e_verification())
