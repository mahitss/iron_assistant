"""CLI interface for Kairo Autonomous Mission Control, Long-Horizon Execution & Continuous Objective Orchestration (Task 100).

Commands:
    python -m app.missions.cli missions list
    python -m app.missions.cli missions get <mission_id>
    python -m app.missions.cli missions inspect <mission_id>
    python -m app.missions.cli missions timeline <mission_id>
    python -m app.missions.cli missions progress <mission_id>
    python -m app.missions.cli missions health <mission_id>
    python -m app.missions.cli missions milestones <mission_id>
    python -m app.missions.cli missions blockers <mission_id>
    python -m app.missions.cli missions assumptions <mission_id>
    python -m app.missions.cli missions review <mission_id> --type PERIODIC --score 0.95 --notes "All milestones healthy"
    python -m app.missions.cli missions reassess <mission_id>
    python -m app.missions.cli missions pause <mission_id> --reason "Operator manual hold"
    python -m app.missions.cli missions resume <mission_id>
    python -m app.missions.cli missions checkpoint <mission_id> --handoff
    python -m app.missions.cli missions orchestrate <mission_id>
"""

from __future__ import annotations

import json
import sys
from typing import Any
import click

try:
    from app.missions.schemas import (
        MissionReviewRequest,
        MissionStatus,
        ReviewType,
    )
    from app.missions.service import mission_service
except ImportError:
    from backend.app.missions.schemas import (
        MissionReviewRequest,
        MissionStatus,
        ReviewType,
    )
    from backend.app.missions.service import mission_service


@click.group(name="kairo-missions")
def main_cli():
    """Kairo Autonomous Mission Control, Long-Horizon Execution & Continuous Objective Orchestrator CLI."""
    pass


@main_cli.group(name="missions")
def missions_group():
    """Manage autonomous missions, milestones, assumptions, health, checkpoints, and orchestrator cycles."""
    pass


cli = main_cli
missions = missions_group


@missions_group.command(name="list")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--status", "status_filter", default=None, help="Filter by mission status")
@click.option("--limit", default=20, help="Maximum missions to list")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def missions_list(tenant: str, status_filter: str | None, limit: int, json_output: bool):
    """List all autonomous missions."""
    try:
        missions = mission_service.list_missions(tenant_id=tenant)
        if status_filter:
            missions = [m for m in missions if m.status.value.upper() == status_filter.upper()]
        missions = missions[:limit]

        if json_output:
            click.echo(json.dumps([m.model_dump(mode="json") for m in missions], indent=2))
            return

        click.echo(f"\nAutonomous Missions ({len(missions)} found, tenant={tenant}):")
        click.echo("-" * 84)
        click.echo(f"{'Mission ID':<18} {'Status':<16} {'Health':<12} {'Progress':<10} {'Title'}")
        click.echo("-" * 84)
        for m in missions:
            click.echo(
                f"{m.mission_id:<18} {m.status.value:<16} {m.health.value:<12} {m.progress_pct*100:>6.1f}%   {m.title[:30]}"
            )
        click.echo("-" * 84)
    except Exception as exc:
        click.echo(f"Error listing missions: {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="get")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def missions_get(mission_id: str, tenant: str, json_output: bool):
    """Get mission details by ID."""
    try:
        mission = mission_service.get_mission(mission_id, tenant_id=tenant)
        if json_output:
            click.echo(json.dumps(mission.model_dump(mode="json"), indent=2))
            return

        click.echo(f"\nMission Details: {mission.mission_id}")
        click.echo("=" * 60)
        click.echo(f"Title:                 {mission.title}")
        click.echo(f"Objective:             {mission.objective}")
        click.echo(f"Status:                {mission.status.value}")
        click.echo(f"Health:                {mission.health.value}")
        click.echo(f"Autonomy Level:        {mission.autonomy_level.value}")
        click.echo(f"Authority Scope:       {mission.authority_scope.value}")
        click.echo(f"Progress:              {mission.progress_pct * 100:.1f}% (confidence={mission.progress_confidence:.2f})")
        click.echo(f"Strategic Importance:  {mission.strategic_importance:.2f}")
        click.echo(f"Uncertainty:           {mission.uncertainty:.2f}")
        click.echo(f"Active Plan:           {mission.active_plan_id or 'None'} (v{len(mission.plan_versions)})")
        click.echo(f"Milestones:            {len(mission.milestones)}")
        click.echo(f"Assumptions:           {len(mission.assumptions)}")
        click.echo(f"Blockers:              {len(mission.blockers)}")
        click.echo(f"Checkpoints:           {len(mission.checkpoints)}")
        click.echo("=" * 60)
    except Exception as exc:
        click.echo(f"Error getting mission '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="inspect")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
def missions_inspect(mission_id: str, tenant: str):
    """Inspect full autonomous mission state, objectives, health dimensions, and invariants."""
    try:
        mission = mission_service.get_mission(mission_id, tenant_id=tenant)
        health_info = mission_service.get_mission_health(mission_id, tenant_id=tenant)
        milestones = mission_service.get_mission_milestones(mission_id, tenant_id=tenant)
        assumptions = mission_service.get_mission_assumptions(mission_id, tenant_id=tenant)

        click.echo(f"\n=== Autonomous Mission Control Deep Inspection: {mission.mission_id} ===")
        click.echo(f"Title:         {mission.title}")
        click.echo(f"Status:        {mission.status.value} (Version: {mission.version})")
        click.echo(f"Health:        {mission.health.value} (Classification Bottleneck: {health_info.get('classification_reason', 'N/A')})")
        click.echo(f"Autonomy:      {mission.autonomy_level.value} | Scope: {mission.authority_scope.value}")
        click.echo(f"Progress:      {mission.progress_pct * 100:.1f}% (Confidence: {mission.progress_confidence:.2f})")
        click.echo(f"Uncertainty:   {mission.uncertainty:.2f} | Priority: {mission.priority}")

        click.echo("\n--- Health Dimensions (10 Raw Metrics) ---")
        dims = health_info.get("dimensions", {})
        for dim, val in dims.items():
            bar = "#" * int(val * 20)
            click.echo(f"  {dim:<32} {val:>5.2f} [{bar:<20}]")

        click.echo(f"\n--- Milestones ({len(milestones)}) ---")
        for m in milestones:
            ev = f"evidence={len(m.get('evidence', []))}"
            crit = " [CRITICAL PATH]" if m.get("is_critical_path") else ""
            click.echo(f"  - [{m.get('status', 'PENDING'):<10}] {m.get('title')}{crit} ({ev})")

        click.echo(f"\n--- Assumptions ({len(assumptions)}) ---")
        for a in assumptions:
            click.echo(f"  - [{a.get('status', 'VALID'):<12}] {a.get('statement')[:50]} (validity={a.get('validity_score', 1.0):.2f})")

        click.echo(f"\n--- Active Plan & Checkpoints ---")
        click.echo(f"  Active Plan ID: {mission.active_plan_id}")
        click.echo(f"  Plan Versions:  {len(mission.plan_versions)}")
        click.echo(f"  Checkpoints:    {len(mission.checkpoints)}")
        click.echo("=" * 72)
    except Exception as exc:
        click.echo(f"Error inspecting mission '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="timeline")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def missions_timeline(mission_id: str, tenant: str, json_output: bool):
    """Retrieve complete audit timeline, replans, and event history."""
    try:
        timeline = mission_service.get_mission_timeline(mission_id, tenant_id=tenant)
        if json_output:
            click.echo(json.dumps(timeline, indent=2))
            return

        click.echo(f"\nTimeline for Mission {mission_id}:")
        click.echo("-" * 72)
        events = timeline.get("audit_events", [])
        for ev in events:
            ts = ev.get("timestamp", "N/A")
            etype = ev.get("event_type", "UNKNOWN")
            actor = ev.get("actor", "system")
            h = ev.get("record_hash", "")[:8]
            click.echo(f"[{ts}] {etype:<26} actor={actor:<10} hash={h}")
        click.echo("-" * 72)
    except Exception as exc:
        click.echo(f"Error retrieving timeline for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="progress")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def missions_progress(mission_id: str, tenant: str, json_output: bool):
    """Show multi-metric progress calculations, confidence, and sunk cost."""
    try:
        progress = mission_service.get_mission_progress(mission_id, tenant_id=tenant)
        if json_output:
            click.echo(json.dumps(progress, indent=2))
            return

        pct = progress.get("progress_pct", 0.0) * 100
        conf = progress.get("confidence", 1.0)
        click.echo(f"\nProgress for Mission {mission_id}:")
        click.echo(f"  Completion: {pct:.1f}%")
        click.echo(f"  Confidence: {conf:.2f}")
        click.echo(f"  Status:     {progress.get('status', 'UNKNOWN')}")
        click.echo(f"  Milestones: {progress.get('completed_milestones', 0)}/{progress.get('total_milestones', 0)} completed")
        if "sunk_cost_usd" in progress:
            click.echo(f"  Sunk Cost:  ${progress.get('sunk_cost_usd', 0.0):.2f}")
    except Exception as exc:
        click.echo(f"Error retrieving progress for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="health")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def missions_health(mission_id: str, tenant: str, json_output: bool):
    """Display 10 raw health dimensions and transparent health classification."""
    try:
        health_info = mission_service.get_mission_health(mission_id, tenant_id=tenant)
        if json_output:
            click.echo(json.dumps(health_info, indent=2))
            return

        click.echo(f"\nHealth Telemetry for Mission {mission_id}:")
        click.echo(f"  Classification: {health_info.get('health', 'UNKNOWN')}")
        click.echo(f"  Reason:         {health_info.get('classification_reason', 'N/A')}")
        click.echo("-" * 60)
        dims = health_info.get("dimensions", {})
        for dim, val in dims.items():
            click.echo(f"  {dim:<32}: {val:.3f}")
        click.echo("-" * 60)
    except Exception as exc:
        click.echo(f"Error getting health for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="milestones")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def missions_milestones(mission_id: str, tenant: str, json_output: bool):
    """List milestones with completion, regression status, and evidence verification."""
    try:
        milestones = mission_service.get_mission_milestones(mission_id, tenant_id=tenant)
        if json_output:
            click.echo(json.dumps(milestones, indent=2))
            return

        click.echo(f"\nMilestones for Mission {mission_id} ({len(milestones)}):")
        click.echo("-" * 76)
        click.echo(f"{'ID':<14} {'Status':<14} {'Crit':<6} {'Evidence':<10} {'Title'}")
        click.echo("-" * 76)
        for m in milestones:
            crit = "YES" if m.get("is_critical_path") else "NO"
            ev_count = len(m.get("evidence", []))
            click.echo(
                f"{m.get('milestone_id', ''):<14} {m.get('status', 'PENDING'):<14} {crit:<6} {ev_count:<10} {m.get('title', '')[:30]}"
            )
        click.echo("-" * 76)
    except Exception as exc:
        click.echo(f"Error getting milestones for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="blockers")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def missions_blockers(mission_id: str, tenant: str, json_output: bool):
    """List prioritized blockers halting mission progression."""
    try:
        blockers = mission_service.get_mission_blockers(mission_id, tenant_id=tenant)
        if json_output:
            click.echo(json.dumps(blockers, indent=2))
            return

        click.echo(f"\nBlockers for Mission {mission_id} ({len(blockers)}):")
        if not blockers:
            click.echo("  No active blockers. Progress unconstrained.")
            return
        for b in blockers:
            click.echo(f"  - [{b.get('severity', 'MEDIUM')}] {b.get('description')} (status={b.get('status', 'ACTIVE')})")
    except Exception as exc:
        click.echo(f"Error getting blockers for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="assumptions")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def missions_assumptions(mission_id: str, tenant: str, json_output: bool):
    """List tracked operational assumptions and their validity status."""
    try:
        assumptions = mission_service.get_mission_assumptions(mission_id, tenant_id=tenant)
        if json_output:
            click.echo(json.dumps(assumptions, indent=2))
            return

        click.echo(f"\nAssumptions for Mission {mission_id} ({len(assumptions)}):")
        for a in assumptions:
            click.echo(f"  - [{a.get('status', 'VALID'):<10}] Score={a.get('validity_score', 1.0):.2f} | {a.get('statement')}")
    except Exception as exc:
        click.echo(f"Error getting assumptions for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="review")
@click.argument("mission_id")
@click.option("--type", "review_type", default="PERIODIC", help="Review type: PERIODIC, POST_INCIDENT, DRIFT_TRIGGERED, RECOVERY")
@click.option("--score", default=1.0, type=float, help="Evaluation score (0.0 to 1.0)")
@click.option("--notes", default="Routine CLI review", help="Review observations")
@click.option("--tenant", default="default", help="Tenant ID")
def missions_review(mission_id: str, review_type: str, score: float, notes: str, tenant: str):
    """Record a formal structured review for a mission."""
    try:
        req = MissionReviewRequest(
            review_type=ReviewType(review_type.upper()),
            evaluation_score=score,
            observations=[notes],
        )
        review = mission_service.record_mission_review(mission_id, req, reviewer="cli_operator", tenant_id=tenant)
        click.echo(f"Successfully recorded review '{review.review_id}' for mission '{mission_id}' (score={score}).")
    except Exception as exc:
        click.echo(f"Error recording review for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="reassess")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
def missions_reassess(mission_id: str, tenant: str):
    """Revalidate assumptions against world model and trigger replanning if invalidated."""
    try:
        result = mission_service.reassess_mission(mission_id, tenant_id=tenant)
        click.echo(f"\nReassessment completed for Mission {mission_id}:")
        click.echo(f"  Assumptions Valid: {result.get('assumptions_valid')}")
        click.echo(f"  Replanned:         {result.get('replanned')}")
        click.echo(f"  New Plan ID:       {result.get('new_plan_id', 'N/A')}")
    except Exception as exc:
        click.echo(f"Error reassessing mission '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="pause")
@click.argument("mission_id")
@click.option("--reason", default="Manual operator pause via CLI", help="Pause reason")
@click.option("--tenant", default="default", help="Tenant ID")
def missions_pause(mission_id: str, reason: str, tenant: str):
    """Pause an active mission safely."""
    try:
        mission = mission_service.pause_mission(mission_id, reason=reason, tenant_id=tenant)
        click.echo(f"Mission '{mission_id}' paused successfully. Status: {mission.status.value}")
    except Exception as exc:
        click.echo(f"Error pausing mission '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="resume")
@click.argument("mission_id")
@click.option("--tenant", default="default", help="Tenant ID")
def missions_resume(mission_id: str, tenant: str):
    """Resume a paused mission with state revalidation."""
    try:
        mission = mission_service.resume_mission(mission_id, tenant_id=tenant)
        click.echo(f"Mission '{mission_id}' resumed successfully. Status: {mission.status.value}")
    except Exception as exc:
        click.echo(f"Error resuming mission '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="checkpoint")
@click.argument("mission_id")
@click.option("--label", default="CLI Checkpoint", help="Checkpoint descriptive label")
@click.option("--handoff", is_flag=True, help="Generate zero-hidden-state handoff manifest")
@click.option("--tenant", default="default", help="Tenant ID")
def missions_checkpoint(mission_id: str, label: str, handoff: bool, tenant: str):
    """Trigger durable checkpoint with optional zero-hidden-state handoff manifest."""
    try:
        cp = mission_service.create_checkpoint(
            mission_id=mission_id,
            label=label,
            generate_handoff_manifest=handoff,
            tenant_id=tenant,
        )
        click.echo(f"\nCheckpoint created: {cp.checkpoint_id}")
        click.echo(f"  Mission: {cp.mission_id} (Status: {cp.status})")
        click.echo(f"  Label:   {cp.label}")
        if cp.handoff_manifest:
            click.echo(f"  Handoff Manifest Generated: {len(cp.handoff_manifest)} keys")
    except Exception as exc:
        click.echo(f"Error creating checkpoint for '{mission_id}': {exc}", err=True)
        sys.exit(1)


@missions_group.command(name="orchestrate")
@click.argument("mission_id")
@click.option("--entity-id", default=None, help="Target World State Entity ID to verify against")
@click.option("--tenant", default="default", help="Tenant ID")
def missions_orchestrate(mission_id: str, entity_id: str | None, tenant: str):
    """Execute one autonomous continuous orchestration cycle (Task 100).

    Continuous loop: ASSESS -> PLAN -> SELECT -> EXECUTE -> OBSERVE -> VERIFY -> UPDATE -> REASSESS.
    """
    try:
        result = mission_service.run_orchestration_cycle(
            mission_id=mission_id,
            world_state_entity_id=entity_id,
            tenant_id=tenant,
        )
        click.echo(f"\nContinuous Orchestration Cycle Completed for Mission {mission_id}:")
        click.echo(f"  Cycle Status:      {result.get('cycle_status')}")
        click.echo(f"  Phase:             {result.get('phase')}")
        click.echo(f"  Mission Status:    {result.get('mission_status')}")
        click.echo(f"  Emergency Stopped: {result.get('emergency_stopped', False)}")
        click.echo(f"  Action Executed:   {result.get('action_executed', False)}")
        if result.get("verification"):
            click.echo(f"  Verified Postcondition: {result.get('verification', {}).get('verified')}")
        click.echo("=" * 60)
    except Exception as exc:
        click.echo(f"Error executing orchestration cycle for '{mission_id}': {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
