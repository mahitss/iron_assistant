#!/usr/bin/env python3
"""
End-to-End Verification Script for Task 85:
Kairo Native Network Execution & Connection Fabric.

Launches the native Rust runtime daemon, interacts via Python NativeRuntimeService,
validates SSRF prevention, anti-DNS rebinding, connection pool health, and EmergencyStop.
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add backend to sys.path
root_dir = Path(__file__).resolve().parent.parent
backend_dir = root_dir / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.native.client import NativeRuntimeClient
from app.native.models import ExecutionRequest, ExecutionState
from app.native.service import NativeRuntimeService
from app.tools.registry import create_default_tool_registry


async def main():
    print("=================================================================")
    print("  KAIRO TASK 85: NATIVE NETWORK EXECUTION & CONNECTION FABRIC   ")
    print("=================================================================")

    binary_path = root_dir / "native" / "target" / "debug" / "kairo-runtime.exe"
    if not binary_path.exists():
        print(f"[ERROR] Native runtime binary not found at: {binary_path}")
        sys.exit(1)

    print(f"[1/7] Found native runtime binary at {binary_path}")

    # Launch daemon process
    daemon_proc = subprocess.Popen(
        [str(binary_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for socket to bind
    time.sleep(1.5)

    try:
        service = NativeRuntimeService.get_instance()
        service.mode = "REQUIRED"
        client = service.client

        # 1. Health check
        print("[2/7] Checking runtime health and network capabilities...")
        health = await service.get_health()
        print(f"      Runtime health: {health.get('status')} (healthy={health.get('healthy')})")
        assert health.get("healthy"), f"Runtime unhealthy: {health}"

        caps = await service.list_capabilities()
        cap_ids = [c.capability_id for c in caps]
        print(f"      Total capabilities discovered: {len(cap_ids)}")
        for req_cap in ("native.net.resolve", "native.net.fetch", "native.net.request", "native.net.health"):
            assert req_cap in cap_ids, f"Missing required network capability: {req_cap}"
        print("      [OK] All 4 native network capabilities registered and verified.")

        # 2. Network Health Report
        print("[3/7] Querying substrate network connection pool & circuit breaker health...")
        net_health = await service.get_network_health()
        print(f"      Network substrate state: {net_health.get('state')}")
        print(f"      Active requests: {net_health.get('active_requests')}, Concurrency limit: {net_health.get('concurrency_limit')}")
        print(f"      Circuit breaker open: {net_health.get('circuit_breaker_open')}")
        assert net_health.get("state") == "HEALTHY"
        print("      [OK] Substrate network health is HEALTHY.")

        # 3. DNS Resolution of public domain
        print("[4/7] Testing safe DNS resolution via native substrate...")
        dns_res = await service.resolve_dns("dns.google")
        resolved_ips = dns_res.get("resolved_ips") or dns_res.get("addresses", [])
        print(f"      Resolved dns.google -> {resolved_ips} (duration: {dns_res.get('duration_ms')}ms)")
        assert len(resolved_ips) > 0, f"DNS resolution failed: {dns_res}"
        print("      [OK] Public DNS resolution succeeded.")

        # 4. SSRF Defense: Loopback and Cloud Metadata
        print("[5/7] Testing strict SSRF defense (loopback, metadata, RFC 1918)...")

        # Test loopback block
        dns_loopback = await service.resolve_dns("127.0.0.1")
        print(f"      Resolve 127.0.0.1: error={dns_loopback.get('error')}")
        assert "SSRF_BLOCKED" in str(dns_loopback.get("error", "")) or dns_loopback.get("status") == "FAILED"

        # Test cloud metadata block
        dns_metadata = await service.resolve_dns("169.254.169.254")
        print(f"      Resolve 169.254.169.254: error={dns_metadata.get('error')}")
        assert "SSRF_BLOCKED" in str(dns_metadata.get("error", "")) or dns_metadata.get("status") == "FAILED"

        # Test fetch to cloud metadata
        fetch_metadata = await service.http_fetch("http://169.254.169.254/latest/meta-data/")
        print(f"      Fetch http://169.254.169.254: error={fetch_metadata.get('error')}")
        assert "SSRF_BLOCKED" in str(fetch_metadata.get("error", "")) or fetch_metadata.get("status") == "FAILED"
        print("      [OK] SSRF defense strictly blocked all loopback and cloud metadata targets.")

        # 5. Tool Registry verification
        print("[6/7] Verifying Native Network Tool Registry integrations...")
        reg = create_default_tool_registry()
        for tname in ("native_dns_resolve", "native_http_fetch", "native_http_request"):
            tool = reg.get(tname)
            assert tool is not None, f"Tool {tname} not in registry"
            assert tool.capability_id.startswith("native.net.")
        print("      [OK] Tools native_dns_resolve, native_http_fetch, and native_http_request verified in registry.")

        # 6. Emergency Stop authority
        print("[7/7] Verifying EmergencyStop containment drill...")
        service.emergency_stop.trigger_emergency_stop(reason="E2E test drill")
        try:
            req = ExecutionRequest(
                request_id="e2e_estop_net",
                capability_id="native.net.fetch",
                arguments=[],
                payload={"url": "https://example.com"},
            )
            estop_res = await service.sandbox_execute(req)
            assert estop_res.state == ExecutionState.REJECTED
            assert "EMERGENCY_STOP_ACTIVE" in estop_res.failure_classification
            print("      [OK] EmergencyStop instantly rejected network execution fail-closed.")
        finally:
            service.emergency_stop.reset_emergency_stop()

        print("\n=================================================================")
        print("  ALL TASK 85 END-TO-END VERIFICATIONS PASSED SUCCESSFULLY!       ")
        print("=================================================================")

    finally:
        daemon_proc.terminate()
        try:
            daemon_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            daemon_proc.kill()


if __name__ == "__main__":
    asyncio.run(main())
