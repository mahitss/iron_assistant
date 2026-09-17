"""CLI commands for Kairo Autonomous Cognitive Control Plane (Task 102)."""

from __future__ import annotations

import json
import click
from app.control_plane.service import get_control_plane_service


@click.group(name="control")
def control_cli() -> None:
    """Kairo autonomous cognitive control plane & unified operating loop."""
    pass


@control_cli.command(name="status")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def status_command(json_output: bool) -> None:
    """Display high-level operational status, control mode, and loop guard state."""
    service = get_control_plane_service()
    stat = service.get_status()

    if json_output:
        click.echo(json.dumps(stat, indent=2))
        return

    click.secho("\n=== KAIRO COGNITIVE CONTROL PLANE ===", fg="cyan", bold=True)
    click.echo(f"Control Mode:     {stat['control_mode']}")
    e_color = "red" if stat["emergency_stop_active"] else "green"
    click.secho(f"Emergency Stop:   {'ACTIVE (Fail-Closed)' if stat['emergency_stop_active'] else 'INACTIVE'}", fg=e_color, bold=True)
    click.echo(f"Queue Depth:      {stat['queue_depth']}")
    click.echo(f"Total Cycles:     {stat['total_cycles_executed']}")
    click.echo(f"Completed Cycles: {stat['metrics']['completed_cycles']}")
    click.echo(f"No-Action Cycles: {stat['metrics']['no_action_cycles']}")
    cb_color = "red" if stat["metrics"]["circuit_breaker_tripped"] else "green"
    click.secho(f"Loop Guard:       {'TRIPPED' if stat['metrics']['circuit_breaker_tripped'] else 'HEALTHY'}", fg=cb_color, bold=True)
    click.echo("")


@control_cli.command(name="mode")
def mode_command() -> None:
    """Display current derived control mode."""
    service = get_control_plane_service()
    stat = service.get_status()
    click.echo(f"Current Control Mode: {stat['control_mode']}")


@control_cli.command(name="health")
def health_command() -> None:
    """Check control plane and loop-guard circuit breaker health."""
    service = get_control_plane_service()
    stat = service.get_status()
    is_healthy = not stat["metrics"]["circuit_breaker_tripped"]
    color = "green" if is_healthy else "red"
    click.secho(f"Control Plane Status: {'HEALTHY' if is_healthy else 'CIRCUIT_BREAKER_TRIPPED'}", fg=color, bold=True)


@control_cli.command(name="cycles")
@click.option("--limit", default=20, help="Maximum cycles to display")
def cycles_command(limit: int) -> None:
    """List recent control cycles."""
    service = get_control_plane_service()
    cycles = service.list_cycles(limit=limit)

    click.secho(f"\n{'CYCLE ID':<25} {'TRIGGER':<20} {'STATUS':<15} {'RESULT':<20}", bold=True)
    click.echo("-" * 80)

    for c in cycles:
        color = "green" if c.status.value in ("COMPLETED", "NO_ACTION") else ("yellow" if c.status.value == "WAITING" else "red")
        click.secho(
            f"{c.cycle_id:<25} {c.trigger_type.value:<20} {c.status.value:<15} {str(c.result or ''):<20}",
            fg=color,
        )
    click.echo("")


@control_cli.command(name="cycle")
@click.argument("cycle_id")
def cycle_detail_command(cycle_id: str) -> None:
    """Inspect full metadata and execution trace of a specific cycle."""
    service = get_control_plane_service()
    cycle = service.get_cycle(cycle_id)
    if not cycle:
        click.secho(f"Error: Cycle '{cycle_id}' not found.", fg="red")
        return

    click.echo(cycle.model_dump_json(indent=2))


@control_cli.command(name="timeline")
@click.argument("cycle_id")
def timeline_command(cycle_id: str) -> None:
    """Display chronological execution stages for a specific cycle."""
    service = get_control_plane_service()
    timeline = service.get_cycle_timeline(cycle_id)
    if not timeline:
        click.secho(f"Error: Timeline for cycle '{cycle_id}' not found.", fg="red")
        return

    click.secho(f"\n=== TIMELINE: {cycle_id} ===", fg="cyan", bold=True)
    for t in timeline:
        click.echo(f"[{t['stage']}] {t['status']} - {t.get('details', '')} {t.get('reason', '')}")
    click.echo("")


@control_cli.command(name="reassess")
@click.option("--scope", default="SYSTEM", help="Target supervisory scope")
def reassess_command(scope: str) -> None:
    """Trigger an immediate supervisory reassessment pass."""
    service = get_control_plane_service()
    cycle = service.reassess(scope=scope)
    click.secho(f"=== REASSESSMENT CYCLE INITIATED: {cycle.cycle_id} (Status: {cycle.status.value}) ===", fg="green")


control_plane = control_cli
control_plane_cli = control_cli
