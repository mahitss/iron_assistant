"""CLI commands for Kairo Autonomous Self-Model (Task 101)."""

from __future__ import annotations

import json
import click
from app.self_model.service import get_self_model_service


@click.group(name="self-model")
def self_model_cli() -> None:
    """Kairo autonomous self-model, capability awareness & internal state intelligence."""
    pass


@self_model_cli.command(name="status")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def status_command(json_output: bool) -> None:
    """Display high-level operational status and autonomy mode."""
    service = get_self_model_service()
    snap = service.get_current_snapshot()

    if json_output:
        click.echo(snap.model_dump_json(indent=2))
        return

    click.secho("\n=== KAIRO SELF-MODEL STATUS ===", fg="cyan", bold=True)
    click.echo(f"Snapshot ID:     {snap.snapshot_id}")
    click.echo(f"Created At:      {snap.created_at}")
    click.echo(f"Runtime Version: {snap.runtime_version}")
    click.echo(f"Autonomy Mode:   {snap.autonomy_mode.value}")
    e_color = "red" if snap.emergency_stop_state else "green"
    click.secho(f"Emergency Stop:  {'ACTIVE' if snap.emergency_stop_state else 'INACTIVE'}", fg=e_color, bold=True)
    click.echo(f"Capabilities:    {len(snap.capabilities)} total")
    click.echo(f"Resource Sat:    {round(snap.resources.saturation_pct * 100, 1)}% ({snap.resources.degradation_tier})")
    click.echo(f"Limitations:     {len(snap.limitations)}")
    click.echo(f"Uncertainties:   {len(snap.uncertainties)}\n")


@self_model_cli.command(name="capabilities")
def capabilities_command() -> None:
    """List capabilities with grounded readiness states and verification evidence."""
    service = get_self_model_service()
    caps = service.get_capabilities()

    click.secho(f"\n{'CAPABILITY ID':<25} {'VERSION':<10} {'STATE':<12} {'READINESS':<12} {'FAILURES':<10}", bold=True)
    click.echo("-" * 75)

    for cap_id, c in caps.items():
        color = "green" if c.readiness_state.value == "READY" else ("yellow" if c.readiness_state.value == "DEGRADED" else "red")
        click.secho(
            f"{cap_id:<25} {c.version:<10} {c.lifecycle_state:<12} {c.readiness_state.value:<12} {c.consecutive_failures:<10}",
            fg=color,
        )
    click.echo("")


@self_model_cli.command(name="limitations")
def limitations_command() -> None:
    """Display factual, evidence-backed self-limitations."""
    service = get_self_model_service()
    lims = service.get_limitations()

    click.secho("\n=== ACTIVE SELF-LIMITATIONS ===", fg="yellow", bold=True)
    if not lims:
        click.echo("No operational limitations detected.")
    for l in lims:
        click.secho(f"[{l.subject}] {l.description}", bold=True)
        click.echo(f"  Reason:   {l.reason}")
        click.echo(f"  Evidence: {l.evidence}\n")


@self_model_cli.command(name="uncertainties")
def uncertainties_command() -> None:
    """Display active epistemic uncertainties."""
    service = get_self_model_service()
    uncs = service.get_uncertainties()

    click.secho("\n=== EPISTEMIC UNCERTAINTIES ===", fg="magenta", bold=True)
    if not uncs:
        click.echo("No active uncertainties.")
    for u in uncs:
        click.secho(f"[{u.subject}] Reason: {u.reason}", bold=True)
        click.echo(f"  Evidence: {u.evidence}")
        click.echo(f"  Policy:   {u.revalidation_policy}\n")


@self_model_cli.command(name="answers")
def answers_command() -> None:
    """Output answers to the 15 canonical introspective questions."""
    service = get_self_model_service()
    ans = service.get_answers()

    click.secho("\n=== 15 CANONICAL INTROSPECTIVE ANSWERS ===", fg="cyan", bold=True)
    click.echo(f"1.  Capabilities:         {', '.join(ans.q1_capabilities)}")
    click.echo(f"2.  Versions:             {ans.q2_versions}")
    click.echo(f"3.  Ready:                {', '.join(ans.q3_ready_capabilities)}")
    click.echo(f"4.  Degraded:             {', '.join(ans.q4_degraded_capabilities) or 'None'}")
    click.echo(f"5.  Unavailable:          {', '.join(ans.q5_temporarily_unavailable) or 'None'}")
    click.echo(f"6.  Resource Saturation:  {round(ans.q6_current_resources.saturation_pct * 100, 1)}%")
    click.echo(f"7.  Usable Tools:         {len(ans.q7_usable_tools)} tools")
    click.echo(f"8.  Authorized Access:    {', '.join(ans.q8_authorized_access)}")
    click.echo(f"9.  Approval Required:    {', '.join(ans.q9_actions_requiring_approval) or 'None'}")
    click.echo(f"10. Failing Dependencies: {', '.join(ans.q10_failing_dependencies) or 'None'}")
    click.echo(f"11. Recently Failed:      {', '.join(ans.q11_recently_failed_capabilities) or 'None'}")
    click.echo(f"12. Reliability Scores:   {ans.q12_capability_reliability}")
    click.echo(f"13. Changes Since Last:   {len(ans.q13_changes_since_last_check)} events")
    click.echo(f"14. Limitations Count:    {len(ans.q14_limitations)}")
    click.echo(f"15. Uncertainties Count:  {len(ans.q15_uncertainties)}\n")


@self_model_cli.command(name="reconcile")
def reconcile_command() -> None:
    """Trigger an immediate empirical state reconciliation pass."""
    service = get_self_model_service()
    snap = service.reconcile()
    click.secho(f"Reconciliation pass complete. New Snapshot ID: {snap.snapshot_id}", fg="green")
