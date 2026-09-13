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
    from app.native.service import NativeRuntimeService
except ImportError:
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


if __name__ == "__main__":
    native_cli()
