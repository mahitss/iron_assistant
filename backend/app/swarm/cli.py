"""CLI interface for Kairo Autonomous Multi-Agent Collaboration & Swarm Orchestration (Task 96).

Usage:
    python -m backend.app.swarm.cli swarm list
    python -m backend.app.swarm.cli swarm inspect <id>
    python -m backend.app.swarm.cli swarm graph <id>
    python -m backend.app.swarm.cli swarm cancel <id>
    python -m backend.app.swarm.cli swarm reconcile <id>

    python -m backend.app.swarm.cli agent list
    python -m backend.app.swarm.cli agent inspect <id>
    python -m backend.app.swarm.cli agent tasks <id>
    python -m backend.app.swarm.cli agent cancel <id>
    python -m backend.app.swarm.cli agent retry <id>
    python -m backend.app.swarm.cli agent reassign <id> <role>
"""

from __future__ import annotations

import asyncio
import json
import sys
import click

try:
    from app.swarm.orchestration_domain import AgentRole
    from app.swarm.orchestration_service import get_swarm_orchestration_service
except ImportError:
    from backend.app.swarm.orchestration_domain import AgentRole
    from backend.app.swarm.orchestration_service import get_swarm_orchestration_service


@click.group(name="kairo-swarm")
def main_cli():
    """Kairo Swarm Orchestration and Multi-Agent Collaboration CLI."""
    pass


# ------------------------------------------------------------------------------
# Swarm Subcommands
# ------------------------------------------------------------------------------

@main_cli.group(name="swarm")
def swarm_group():
    """Manage collective swarm sessions and topologies."""
    pass


@swarm_group.command(name="list")
@click.option("--limit", default=20, help="Maximum sessions to list")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def swarm_list(limit: int, json_output: bool):
    """List recent swarm collaboration sessions."""
    service = get_swarm_orchestration_service()
    sessions = service.list_sessions(limit=limit)
    if json_output:
        click.echo(json.dumps([s.model_dump() for s in sessions], indent=2, default=str))
        return

    click.echo(f"\n{'SWARM ID':<36} | {'STATUS':<12} | {'OBJECTIVE':<40}")
    click.echo("-" * 95)
    for s in sessions:
        click.echo(f"{s.session_id:<36} | {s.status.value:<12} | {s.objective.goal[:38]:<40}")
    click.echo(f"\nTotal: {len(sessions)} swarm sessions\n")


@swarm_group.command(name="inspect")
@click.argument("session_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def swarm_inspect(session_id: str, json_output: bool):
    """Inspect a specific swarm session."""
    service = get_swarm_orchestration_service()
    s = service.get_session(session_id)
    if not s:
        click.echo(f"Error: Swarm '{session_id}' not found.", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(s.model_dump(), indent=2, default=str))
        return

    click.echo("\n=======================================================")
    click.echo(f"  SWARM COLLABORATION SESSION: {s.session_id}")
    click.echo("=======================================================")
    click.echo(f"  Status:       {s.status.value}")
    click.echo(f"  Objective:    {s.objective.goal}")
    click.echo(f"  Created:      {s.created_at}")
    click.echo(f"  Topology:     {s.topology.value}")
    click.echo(f"  Agents:       {len(s.agent_specs)}")
    click.echo(f"  Tasks:        {len(s.task_dag.nodes)}")
    if s.final_result:
        click.echo("\n  [Final Synthesis]")
        click.echo(f"  Summary:      {s.final_result.summary}")
        click.echo(f"  Verification: {s.final_result.verification_status}")
    click.echo("=======================================================\n")


@swarm_group.command(name="graph")
@click.argument("session_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def swarm_graph(session_id: str, json_output: bool):
    """Render the DAG graph topology for a swarm."""
    service = get_swarm_orchestration_service()
    graph = service.get_swarm_graph(session_id)
    if json_output:
        click.echo(json.dumps(graph, indent=2))
        return

    click.echo(f"\nSwarm DAG Topology: {session_id}")
    click.echo(f"Nodes ({len(graph['nodes'])}):")
    for n in graph["nodes"]:
        click.echo(f"  [{n['type'].upper()}] {n['id']} -> {n['label']} ({n['state']})")
    click.echo(f"Edges ({len(graph['edges'])}):")
    for e in graph["edges"]:
        click.echo(f"  {e['source']} --({e['type']})--> {e['target']}")
    click.echo("")


@swarm_group.command(name="cancel")
@click.argument("session_id")
@click.option("--reason", default="Operator CLI cancellation", help="Cancellation reason")
def swarm_cancel(session_id: str, reason: str):
    """Cancel a swarm session and all its active agent workers."""
    service = get_swarm_orchestration_service()
    try:
        asyncio.run(service.cancel_swarm(session_id, reason=reason))
        click.echo(f"Swarm '{session_id}' and all child workers successfully CANCELLED.")
    except KeyError:
        click.echo(f"Error: Swarm '{session_id}' not found.", err=True)
        sys.exit(1)


@swarm_group.command(name="reconcile")
@click.argument("session_id")
def swarm_reconcile(session_id: str):
    """Reconcile dangling or unverified states in a swarm."""
    service = get_swarm_orchestration_service()
    try:
        res = service.reconcile_swarm(session_id)
        click.echo(f"Reconciliation completed: {res['reconciled_agents_count']} agents terminated.")
    except KeyError:
        click.echo(f"Error: Swarm '{session_id}' not found.", err=True)
        sys.exit(1)


# ------------------------------------------------------------------------------
# Agent Subcommands
# ------------------------------------------------------------------------------

@main_cli.group(name="agent")
def agent_group():
    """Inspect and control individual bounded agent workers."""
    pass


@agent_group.command(name="list")
@click.option("--session-id", default=None, help="Filter by swarm session ID")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def agent_list(session_id: str | None, json_output: bool):
    """List agent workers."""
    service = get_swarm_orchestration_service()
    agents = service.list_agents(session_id=session_id)
    if json_output:
        click.echo(json.dumps([a.to_dict() for a in agents], indent=2))
        return

    click.echo(f"\n{'AGENT ID':<36} | {'ROLE':<16} | {'STATE':<14} | {'TRUST':<6}")
    click.echo("-" * 80)
    for a in agents:
        click.echo(f"{a.agent_id:<36} | {a.role.value:<16} | {a.lifecycle_state.value:<14} | {a.trust_score:.2f}")
    click.echo(f"\nTotal: {len(agents)} agents\n")


@agent_group.command(name="inspect")
@click.argument("agent_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def agent_inspect(agent_id: str, json_output: bool):
    """Inspect an agent worker's identity and scoped boundaries."""
    service = get_swarm_orchestration_service()
    a = service.get_agent(agent_id)
    if not a:
        click.echo(f"Error: Agent '{agent_id}' not found.", err=True)
        sys.exit(1)

    if json_output:
        click.echo(json.dumps(a.to_dict(), indent=2))
        return

    click.echo("\n=======================================================")
    click.echo(f"  AGENT WORKER: {a.agent_id}")
    click.echo("=======================================================")
    click.echo(f"  Role:             {a.role.value}")
    click.echo(f"  Session ID:       {a.session_id}")
    click.echo(f"  Parent Agent:     {a.parent_agent_id or 'None (Root)'}")
    click.echo(f"  State:            {a.lifecycle_state.value}")
    click.echo(f"  Trust Score:      {a.trust_score:.2f}")
    click.echo(f"  Context Scope:    {a.context_scope}")
    click.echo(f"  Capabilities:     {', '.join(a.capability_scope) if a.capability_scope else 'READ-ONLY'}")
    click.echo(f"  History Steps:    {len(a.history)}")
    click.echo("=======================================================\n")


@agent_group.command(name="tasks")
@click.argument("agent_id")
@click.option("--json-output", is_flag=True, help="Output as JSON")
def agent_tasks(agent_id: str, json_output: bool):
    """List tasks assigned to a specific agent."""
    service = get_swarm_orchestration_service()
    tasks = service.get_agent_tasks(agent_id)
    if json_output:
        click.echo(json.dumps([t.objective for t in tasks], indent=2))
        return

    click.echo(f"\nTasks for Agent {agent_id}: {len(tasks)}")
    for t in tasks:
        click.echo(f"  [{t.task_id[:8]}] ({t.status}) {t.objective}")
    click.echo("")


@agent_group.command(name="cancel")
@click.argument("agent_id")
@click.option("--reason", default="Operator CLI cancel", help="Cancellation reason")
def agent_cancel(agent_id: str, reason: str):
    """Cancel an individual agent worker."""
    service = get_swarm_orchestration_service()
    try:
        service.cancel_agent(agent_id, reason=reason)
        click.echo(f"Agent '{agent_id}' CANCELLED.")
    except KeyError:
        click.echo(f"Error: Agent '{agent_id}' not found.", err=True)
        sys.exit(1)


@agent_group.command(name="retry")
@click.argument("agent_id")
def agent_retry(agent_id: str):
    """Retry a failed agent worker."""
    service = get_swarm_orchestration_service()
    try:
        service.retry_agent(agent_id)
        click.echo(f"Agent '{agent_id}' RETRIED and returned to RUNNING.")
    except KeyError:
        click.echo(f"Error: Agent '{agent_id}' not found.", err=True)
        sys.exit(1)


@agent_group.command(name="reassign")
@click.argument("agent_id")
@click.argument("role")
def agent_reassign(agent_id: str, role: str):
    """Reassign an agent to a new role."""
    service = get_swarm_orchestration_service()
    try:
        new_role = AgentRole(role.upper())
        service.reassign_agent(agent_id, new_role=new_role)
        click.echo(f"Agent '{agent_id}' successfully reassigned to {new_role.value}.")
    except ValueError:
        click.echo(f"Error: Invalid role '{role}'. Valid roles: {[r.value for r in AgentRole]}", err=True)
        sys.exit(1)
    except KeyError:
        click.echo(f"Error: Agent '{agent_id}' not found.", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
