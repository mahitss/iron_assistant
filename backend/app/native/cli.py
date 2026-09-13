"""
CLI interface for Kairo Native Runtime inspection and operations.
Usage:
    python -m backend.app.native.cli status
    python -m backend.app.native.cli ping
    python -m backend.app.native.cli capabilities
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Optional
import click

try:
    from app.native.models import ExecutionRequest, SandboxPolicy, SandboxProfile
    from app.native.service import NativeRuntimeService
except ImportError:
    from backend.app.native.models import ExecutionRequest, SandboxPolicy, SandboxProfile
    from backend.app.native.service import NativeRuntimeService



@click.group(name="native")
def native_cli():
    """Kairo Native Runtime Foundation CLI Commands."""
    pass


@native_cli.command(name="status")
@click.option("--json-output", is_flag=True, help="Output status as raw JSON")
def status_cmd(json_output: bool):
    """Check the health and lifecycle state of the native runtime substrate."""
    async def _run():
        service = NativeRuntimeService.get_instance()
        health = await service.get_health()
        if json_output:
            click.echo(json.dumps(health, indent=2))
        else:
            click.echo("========================================")
            click.echo("  KAIRO NATIVE RUNTIME SUBSTRATE STATUS")
            click.echo("========================================")
            click.echo(f"  Mode:     {health.get('mode')}")
            click.echo(f"  Status:   {health.get('status')}")
            click.echo(f"  Healthy:  {health.get('healthy')}")
            click.echo(f"  Message:  {health.get('message')}")
            metadata = health.get("metadata")
            if metadata:
                click.echo("----------------------------------------")
                click.echo(f"  Runtime Version:   {metadata.get('runtime_version')}")
                click.echo(f"  Protocol Version:  {metadata.get('protocol_version')}")
                click.echo(f"  Platform:          {metadata.get('platform')} ({metadata.get('arch')})")
                click.echo(f"  Uptime (seconds):  {metadata.get('uptime_seconds')}")
                click.echo(f"  Active Requests:   {metadata.get('active_requests')}")
                click.echo(f"  Capabilities:      {', '.join(metadata.get('capabilities', []))}")
            click.echo("========================================")

    asyncio.run(_run())


@native_cli.command(name="ping")
@click.option("--message", default="cli_ping", help="Ping payload message")
def ping_cmd(message: str):
    """Send a ping probe to verify native runtime connectivity."""
    async def _run():
        service = NativeRuntimeService.get_instance()
        resp = await service.execute(
            operation="sys.ping",
            payload={"message": message},
        )
        click.echo(json.dumps(resp.model_dump(), indent=2, default=str))

    asyncio.run(_run())


@native_cli.command(name="capabilities")
def capabilities_cmd():
    """List all registered native capabilities."""
    async def _run():
        service = NativeRuntimeService.get_instance()
        caps = await service.list_capabilities()
        click.echo(f"Found {len(caps)} registered native capabilities:")
        for cap in caps:
            click.echo(f" - [{cap.capability_id}] {cap.name} (v{cap.version}) - {cap.execution_class.value}")
            click.echo(f"   {cap.description}")

    asyncio.run(_run())


# =============================================================================
# Sandbox Subcommands (Task 81)
# =============================================================================

@native_cli.group(name="sandbox")
def sandbox_group():
    """Native Secure Execution Sandbox management commands."""
    pass


@sandbox_group.command(name="preflight")
@click.argument("capability_id", default="sandbox.echo")
@click.option("--profile", type=click.Choice(["MINIMAL", "STANDARD", "STRICT"]), default="STANDARD")
def sandbox_preflight_cmd(capability_id: str, profile: str):
    """Evaluate preflight dry-run and policy intersection for a capability."""
    async def _run():
        service = NativeRuntimeService.get_instance()
        req = ExecutionRequest(
            capability_id=capability_id,
            sandbox_policy=SandboxPolicy(profile=SandboxProfile(profile)),
        )
        result = await service.sandbox_preflight(req)
        click.echo(json.dumps(result.model_dump(), indent=2, default=str))

    asyncio.run(_run())


@sandbox_group.command(name="execute")
@click.argument("capability_id", default="sandbox.echo")
@click.option("--message", default="Hello from native sandbox CLI", help="Message for echo capability")
@click.option("--profile", type=click.Choice(["MINIMAL", "STANDARD", "STRICT"]), default="STANDARD")
@click.option("--approval-id", default=None, help="Approval ID if capability requires it")
def sandbox_execute_cmd(capability_id: str, message: str, profile: str, approval_id: Optional[str]):
    """Execute a sandboxed native capability within the Rust isolation environment."""
    async def _run():
        service = NativeRuntimeService.get_instance()
        req = ExecutionRequest(
            capability_id=capability_id,
            arguments=[message] if capability_id == "sandbox.echo" else [],
            payload={"message": message},
            sandbox_policy=SandboxPolicy(profile=SandboxProfile(profile)),
        )
        result = await service.sandbox_execute(req, approval_id=approval_id)
        click.echo(json.dumps(result.model_dump(), indent=2, default=str))

    asyncio.run(_run())


@sandbox_group.command(name="cancel")
@click.argument("cancellation_id")
def sandbox_cancel_cmd(cancellation_id: str):
    """Cancel an active sandboxed workload by cancellation_id."""
    async def _run():
        service = NativeRuntimeService.get_instance()
        success = await service.cancel(cancellation_id)
        click.echo(json.dumps({"cancellation_id": cancellation_id, "cancelled": success}, indent=2))

    asyncio.run(_run())


# =============================================================================
# Resource Economy Subcommands (Task 82)
# =============================================================================

@native_cli.command(name="economy")
def economy_cmd():
    """Inspect native resource capacities, saturation, and active reservations."""
    service = NativeRuntimeService.get_instance()
    status = service.get_resource_economy_status()
    click.echo("========================================")
    click.echo("  NATIVE RESOURCE ENFORCEMENT & ECONOMY")
    click.echo("========================================")
    click.echo(f"  System Saturation:     {status.get('saturation_pct')}%")
    click.echo(f"  Saturation State:      {status.get('saturation_state')}")
    click.echo(f"  Active Reservations:   {status.get('active_reservations_count')}")
    click.echo("----------------------------------------")
    click.echo("  Registered Substrates:")
    for res in status.get("resources", []):
        click.echo(
            f"   - {res['name']} ({res['resource_id']}) [{res['type']}]: "
            f"Avail {res['available_capacity']:.1f} / Total {res['total_capacity']:.1f} "
            f"(Reserved {res['reserved_capacity']:.1f}, Allocated {res['allocated_capacity']:.1f})"
        )
    click.echo("========================================")


if __name__ == "__main__":
    native_cli()

