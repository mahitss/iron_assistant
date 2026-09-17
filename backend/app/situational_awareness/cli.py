"""CLI interface for Kairo Autonomous Situation Awareness, Signal Fusion & Proactive Response Orchestrator (Task 99).

Usage:
    python -m app.situational_awareness.cli situations list
    python -m app.situational_awareness.cli situations get <id>
    python -m app.situational_awareness.cli situations inspect <id>
    python -m app.situational_awareness.cli situations timeline <id>
    python -m app.situational_awareness.cli situations signals <id>
    python -m app.situational_awareness.cli situations suppress <id> --reason "Maintenance" --duration 3600
    python -m app.situational_awareness.cli situations reopen <id> --reason "Recurred"
    python -m app.situational_awareness.cli situations refresh <id>
    python -m app.situational_awareness.cli situations investigate <id> --scope "deep"
    python -m app.situational_awareness.cli situations stats
"""

from __future__ import annotations

import asyncio
import json
import sys
import click

try:
    from app.situational_awareness.domain import (
        SituationLifecycleState,
        SituationSeverity,
        SituationType,
    )
    from app.situational_awareness.service import situational_awareness_service
except ImportError:
    from backend.app.situational_awareness.domain import (
        SituationLifecycleState,
        SituationSeverity,
        SituationType,
    )
    from backend.app.situational_awareness.service import situational_awareness_service


@click.group(name="kairo-situations")
def main_cli():
    """Kairo Autonomous Situation Awareness and Proactive Response CLI."""
    pass


@main_cli.group(name="situations")
def situations_group():
    """Manage situations, signals, timelines, and proactive responses."""
    pass


@situations_group.command(name="list")
@click.option("--type", "situation_type", default=None, help="Filter by situation type")
@click.option("--state", "lifecycle_state", default=None, help="Filter by lifecycle state")
@click.option("--severity", default=None, help="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)")
@click.option("--limit", default=20, help="Maximum situations to list")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def situations_list(situation_type: str | None, lifecycle_state: str | None, severity: str | None, limit: int, json_output: bool):
    """List detected and active situations."""
    st = SituationType(situation_type) if situation_type else None
    ls = SituationLifecycleState(lifecycle_state) if lifecycle_state else None
    sev = SituationSeverity(severity) if severity else None

    async def _run():
        return await situational_awareness_service.list_situations(
            situation_type=st, lifecycle_state=ls, severity=sev, limit=limit
        )

    sits = asyncio.run(_run())

    if json_output:
        click.echo(json.dumps([s.to_dict() for s in sits], indent=2, default=str))
        return

    click.echo(f"\n{'SITUATION ID':<24} | {'SEVERITY':<10} | {'STATE':<18} | {'TYPE':<16} | {'SIGNALS':<7} | {'TITLE':<32}")
    click.echo("-" * 115)
    for s in sits:
        click.echo(
            f"{s.id:<24} | {s.severity.value:<10} | {s.lifecycle_state.value:<18} | {s.situation_type.value:<16} | {s.signal_count:<7} | {s.title[:30]:<32}"
        )


@situations_group.command(name="get")
@click.argument("situation_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def situations_get(situation_id: str, json_output: bool):
    """Retrieve detailed state of a situation by ID."""
    async def _run():
        return await situational_awareness_service.get_situation(situation_id)

    try:
        sit = asyncio.run(_run())
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(sit.to_dict(), indent=2, default=str))
        return

    click.echo(f"\n=======================================================")
    click.echo(f" SITUATION: {sit.id} ({sit.title})")
    click.echo(f"=======================================================")
    click.echo(f" Type:             {sit.situation_type.value}")
    click.echo(f" State:            {sit.lifecycle_state.value}")
    click.echo(f" Severity:         {sit.severity.value}")
    click.echo(f" Priority:         {sit.priority:.2f}")
    click.echo(f" Confidence:       {sit.confidence:.2f}")
    click.echo(f" Urgency:          {sit.urgency:.2f}")
    click.echo(f" Impact:           {sit.impact:.2f}")
    click.echo(f" Signals:          {sit.signal_count} (from {sit.source_count} sources)")
    click.echo(f" Causal Status:    {sit.causal_status.value}")
    click.echo(f" Reconciliation:   {sit.state_reconciliation_status.value}")
    click.echo(f" Recommended Next: {sit.recommended_next_step or 'None'}")
    click.echo(f" Decision ID:      {sit.current_decision_id or 'None'}")
    click.echo(f" Action Tx ID:     {sit.current_action_transaction_id or 'None'}")
    click.echo(f" Summary:          {sit.summary}")
    click.echo(f" Created:          {sit.created_at.isoformat()}")
    click.echo(f" Updated:          {sit.updated_at.isoformat()}\n")


@situations_group.command(name="inspect")
@click.argument("situation_id")
def situations_inspect(situation_id: str):
    """Deep inspect situation including evidence, affected entities, and decision lineage."""
    async def _run():
        return await situational_awareness_service.get_situation(situation_id)

    try:
        sit = asyncio.run(_run())
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"\n[SITUATION EVIDENCE GRAPH: {sit.id}]")
    click.echo(f"Affected Entities:     {', '.join(sit.affected_entities) or 'None'}")
    click.echo(f"Affected Capabilities: {', '.join(sit.affected_capabilities) or 'None'}")
    click.echo(f"Affected Resources:    {', '.join(sit.affected_resources) or 'None'}")
    click.echo(f"Affected Goals:        {', '.join(sit.affected_goals) or 'None'}")
    click.echo(f"Evidence Items:        {len(sit.evidence)}")
    for i, ev in enumerate(sit.evidence, 1):
        click.echo(f"  {i}. [{ev.get('type', 'OBSERVED')}] {ev.get('source', 'system')}: {ev.get('detail', '')}")
    click.echo("")


@situations_group.command(name="timeline")
@click.argument("situation_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def situations_timeline(situation_id: str, json_output: bool):
    """View chronological signal and lifecycle timeline for situation."""
    async def _run():
        return await situational_awareness_service.get_situation(situation_id)

    try:
        sit = asyncio.run(_run())
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps([e.to_dict() for e in sit.timeline], indent=2, default=str))
        return

    click.echo(f"\n--- Timeline for {sit.id} ({len(sit.timeline)} entries) ---")
    for entry in sit.timeline:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        click.echo(f"[{ts}] [{entry.evidence_type}] [{entry.source}] {entry.summary}")


@situations_group.command(name="signals")
@click.argument("situation_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def situations_signals(situation_id: str, json_output: bool):
    """List all normalized signals correlated into this situation."""
    signals = situational_awareness_service.get_signals_for_situation(situation_id)
    if json_output:
        click.echo(json.dumps([s.to_dict() for s in signals], indent=2, default=str))
        return

    click.echo(f"\n--- Signals correlated into {situation_id} ({len(signals)} total) ---")
    click.echo(f"{'SIGNAL ID':<24} | {'SOURCE':<18} | {'TYPE':<24} | {'CONF':<5} | {'SUBJECT':<35}")
    click.echo("-" * 115)
    for sig in signals:
        click.echo(
            f"{sig.signal_id:<24} | {sig.source_type:<18} | {sig.signal_type:<24} | {sig.confidence:<5.2f} | {sig.subject[:33]:<35}"
        )


@situations_group.command(name="suppress")
@click.argument("situation_id")
@click.option("--reason", required=True, help="Auditable reason for suppression")
@click.option("--duration", default=3600, help="Duration in seconds (default: 3600s)")
@click.option("--actor", default="CLI_USER", help="Actor initiating suppression")
def situations_suppress(situation_id: str, reason: str, duration: int, actor: str):
    """Suppress a situation to silence non-actionable alerts."""
    async def _run():
        return await situational_awareness_service.suppress_situation(
            situation_id=situation_id, suppressed_by=actor, reason=reason, duration_seconds=duration
        )

    try:
        rec = asyncio.run(_run())
        click.echo(f"Situation {situation_id} suppressed until {rec.expires_at.isoformat()} by {actor}. Reason: {reason}")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@situations_group.command(name="reopen")
@click.argument("situation_id")
@click.option("--reason", default="Manual reopen from CLI", help="Reason for reopening")
@click.option("--actor", default="CLI_USER", help="Actor reopening situation")
def situations_reopen(situation_id: str, reason: str, actor: str):
    """Reopen a suppressed or resolved situation."""
    async def _run():
        return await situational_awareness_service.reopen_situation(
            situation_id=situation_id, actor=actor, reason=reason
        )

    try:
        sit = asyncio.run(_run())
        click.echo(f"Situation {situation_id} reopened to state {sit.lifecycle_state.value}.")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@situations_group.command(name="refresh")
@click.argument("situation_id")
def situations_refresh(situation_id: str):
    """Trigger proactive re-deliberation and reality reconciliation check."""
    async def _run():
        return await situational_awareness_service.orchestrate_situation(situation_id)

    try:
        res = asyncio.run(_run())
        click.echo(f"Orchestration cycle completed: {res.get('action_status', 'UNKNOWN')}. Reason: {res.get('reason', '')}")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@situations_group.command(name="investigate")
@click.argument("situation_id")
@click.option("--scope", default=None, help="Optional investigation scope focus")
def situations_investigate(situation_id: str, scope: str | None):
    """Dispatch investigation tasks across bounded agents for evidence gathering."""
    async def _run():
        return await situational_awareness_service.investigate_situation(situation_id, scope=scope)

    try:
        res = asyncio.run(_run())
        click.echo(f"Investigation {res.get('investigation_status')}: {res.get('evidence_count', 0)} evidence items gathered.")
        for ev in res.get("evidence", []):
            click.echo(f"  - [{ev.get('agent', 'agent')}] {ev.get('detail', '')}")
    except Exception as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@situations_group.command(name="stats")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def situations_stats(json_output: bool):
    """Display real-time situational awareness metrics and capacity."""
    stats = situational_awareness_service.get_stats()
    if json_output:
        click.echo(json.dumps(stats, indent=2))
        return

    click.echo("\n--- Kairo Situational Awareness System Stats ---")
    click.echo(f" Total Situations:        {stats['total_situations']}")
    click.echo(f" Active:                  {stats['active_situations']}")
    click.echo(f" Escalating:              {stats['escalating_situations']}")
    click.echo(f" Interventions Active:    {stats['interventions_active']}")
    click.echo(f" Suppressed:              {stats['suppressed_situations']}")
    click.echo(f" Resolved:                {stats['resolved_situations']}")
    click.echo(f" Unknown:                 {stats['unknown_situations']}")
    click.echo(f" Signals Ingested:        {stats['signals_ingested']}")
    click.echo(f" Recurring Patterns:      {stats['patterns_detected']}")
    click.echo(f" Emergency Stop Active:   {stats['emergency_stop_active']}\n")


if __name__ == "__main__":
    main_cli()
