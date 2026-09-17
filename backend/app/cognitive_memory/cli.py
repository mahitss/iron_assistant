"""CLI commands for Kairo Autonomous Cognitive Memory & Lifelong Learning Fabric (Task 103)."""

from __future__ import annotations

import json
from typing import Optional
import click

from app.cognitive_memory.domain import FreshnessState, MemoryLifecycleState, MemoryScope, MemoryType
from app.cognitive_memory.service import get_cognitive_memory_service


@click.group(name="memory")
def memory_cli() -> None:
    """Kairo autonomous cognitive memory, experience consolidation & lifelong learning fabric."""
    pass


@memory_cli.command(name="status")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def status_command(json_output: bool) -> None:
    """Display high-level cognitive memory fabric status and metrics."""
    service = get_cognitive_memory_service()
    stat = service.get_status()

    if json_output:
        click.echo(json.dumps(stat, indent=2))
        return

    click.secho("\n=== KAIRO COGNITIVE MEMORY FABRIC ===", fg="cyan", bold=True)
    click.echo(f"Total Experiences:    {stat['total_experiences']}")
    click.echo(f"Total Memories:       {stat['total_memories']}")
    click.secho(f"Active Memories:      {stat['active_memories']}", fg="green", bold=True)
    click.echo(f"Candidate Memories:   {stat['candidate_memories']}")
    s_color = "yellow" if stat['stale_memories'] > 0 else "green"
    click.secho(f"Stale Memories:       {stat['stale_memories']}", fg=s_color)
    click.echo(f"Superseded Memories:  {stat['superseded_memories']}")
    c_color = "red" if stat['active_conflicts'] > 0 else "green"
    click.secho(f"Active Conflicts:     {stat['active_conflicts']}", fg=c_color, bold=True)
    click.echo(f"Patterns Discovered:  {stat['patterns_discovered']}")
    click.echo(f"Total Applications:   {stat['total_applications']}")
    click.echo(f"Feedback Recorded:    {stat['feedback_recorded']}")
    click.echo("")


@memory_cli.command(name="list")
@click.option("--scope", type=click.Choice([s.value for s in MemoryScope]), help="Filter by scope")
@click.option("--state", type=click.Choice([l.value for l in MemoryLifecycleState]), help="Filter by lifecycle state")
@click.option("--type", "memory_type", type=click.Choice([t.value for t in MemoryType]), help="Filter by memory type")
@click.option("--limit", default=20, help="Maximum memories to list")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def list_command(scope: Optional[str], state: Optional[str], memory_type: Optional[str], limit: int, json_output: bool) -> None:
    """List cognitive memories."""
    service = get_cognitive_memory_service()
    mems = service.list_memories(scope=scope, lifecycle_state=state, memory_type=memory_type, limit=limit)

    if json_output:
        click.echo(json.dumps([m.model_dump() for m in mems], indent=2))
        return

    click.secho(f"\nListing {len(mems)} memories:", fg="cyan", bold=True)
    for m in mems:
        f_color = "green" if m.freshness == FreshnessState.CURRENT else ("yellow" if m.freshness == FreshnessState.RECENT else "red")
        click.echo(f"- [{m.memory_id}] {m.memory_type.value:<12} | {m.scope.value:<8} | conf={m.confidence:.2f} | ", nl=False)
        click.secho(f"{m.freshness.value:<8}", fg=f_color, nl=False)
        click.echo(f" | {m.content[:50]}...")
    click.echo("")


@memory_cli.command(name="get")
@click.argument("memory_id")
@click.option("--json-output", is_flag=True, help="Output raw JSON")
def get_command(memory_id: str, json_output: bool) -> None:
    """Get full details of a specific cognitive memory."""
    service = get_cognitive_memory_service()
    mem = service.get_memory(memory_id)
    if not mem:
        click.secho(f"Memory '{memory_id}' not found.", fg="red")
        return

    if json_output:
        click.echo(json.dumps(mem.model_dump(), indent=2))
        return

    click.secho(f"\n=== Memory {mem.memory_id} (v{mem.version}) ===", fg="cyan", bold=True)
    click.echo(f"Type:        {mem.memory_type.value}")
    click.echo(f"Lifecycle:   {mem.lifecycle_state.value}")
    click.echo(f"Freshness:   {mem.freshness.value}")
    click.echo(f"Scope:       {mem.scope.value} ({mem.scope_id or 'global'})")
    click.echo(f"Provenance:  {mem.provenance_trust.value}")
    click.echo(f"Confidence:  {mem.confidence:.2f}")
    click.echo(f"Observed:    {mem.observed_at}")
    click.echo(f"Content:\n  {mem.content}\n")
    if mem.structured_facts:
        click.echo(f"Structured Facts: {json.dumps(mem.structured_facts, indent=4)}")
    click.echo("")


@memory_cli.command(name="search")
@click.argument("query")
@click.option("--scope", type=click.Choice([s.value for s in MemoryScope]), default="PROJECT", help="Search scope")
@click.option("--limit", default=10, help="Max results")
def search_command(query: str, scope: str, limit: int) -> None:
    """Search cognitive memories by keyword and scope."""
    service = get_cognitive_memory_service()
    results = service.search(query=query, scope=MemoryScope(scope), limit=limit)

    click.secho(f"\nSearch results for '{query}' in scope {scope} ({len(results)} matches):", fg="cyan", bold=True)
    for m in results:
        click.echo(f"- [{m.memory_id}] ({m.memory_type.value}) conf={m.confidence:.2f}: {m.content}")
    click.echo("")


@memory_cli.command(name="history")
@click.argument("memory_id")
def history_command(memory_id: str) -> None:
    """Display version lineage and provenance trail for a memory."""
    service = get_cognitive_memory_service()
    mem = service.get_memory(memory_id)
    if not mem:
        click.secho(f"Memory '{memory_id}' not found.", fg="red")
        return

    click.secho(f"\nHistory & Lineage for {mem.memory_id}:", fg="cyan", bold=True)
    click.echo(f"Current Version:  {mem.version}")
    click.echo(f"Predecessor ID:   {mem.predecessor_id or 'None'}")
    click.echo(f"Superseded By:    {mem.superseded_by or 'None'}")
    click.echo(f"Lineage Chain:    {' -> '.join(mem.lineage_ids) if mem.lineage_ids else 'None'}")
    click.echo("Provenance Trail:")
    for step in mem.provenance_trail:
        click.echo(f"  - {step}")
    click.echo("")


@memory_cli.command(name="evidence")
@click.argument("memory_id")
def evidence_command(memory_id: str) -> None:
    """Display empirical evidence and verification references."""
    service = get_cognitive_memory_service()
    mem = service.get_memory(memory_id)
    if not mem:
        click.secho(f"Memory '{memory_id}' not found.", fg="red")
        return

    click.secho(f"\nEmpirical Evidence for {mem.memory_id}:", fg="cyan", bold=True)
    click.echo(f"Confidence Score:       {mem.confidence:.2f}")
    click.echo(f"Confidence Evidence:    {mem.confidence_evidence}")
    click.echo(f"Evidence Experiences:   {', '.join(mem.evidence_experience_ids) if mem.evidence_experience_ids else 'None'}")
    click.echo(f"Verification Refs:      {', '.join(mem.verification_references) if mem.verification_references else 'None'}")
    click.echo(f"Empirical Applications: Useful={mem.useful_count}, Errors={mem.error_count}")
    click.echo("")


@memory_cli.command(name="conflicts")
def conflicts_command() -> None:
    """Display active memory conflicts and disagreements."""
    service = get_cognitive_memory_service()
    conflicts = service.list_conflicts()

    click.secho(f"\nActive Memory Conflicts ({len(conflicts)}):", fg="cyan", bold=True)
    for c in conflicts:
        click.echo(f"- [{c.conflict_id}] ({c.status}) entity={c.entity_reference}: {c.discrepancy_summary}")
        click.echo(f"    Memory A: {c.competing_memory_a}")
        click.echo(f"    Memory B: {c.competing_memory_b}")
    click.echo("")


@memory_cli.command(name="stale")
def stale_command() -> None:
    """List all memories flagged as STALE."""
    service = get_cognitive_memory_service()
    stale_items = [m for m in service.list_memories(limit=200) if m.freshness == FreshnessState.STALE]

    click.secho(f"\nStale Memories Requiring Revalidation ({len(stale_items)}):", fg="yellow", bold=True)
    for m in stale_items:
        click.echo(f"- [{m.memory_id}] {m.content} (observed {m.observed_at})")
    click.echo("")


@memory_cli.command(name="patterns")
def patterns_command() -> None:
    """List discovered recurring memory patterns."""
    service = get_cognitive_memory_service()
    patterns = service.list_patterns()

    click.secho(f"\nDiscovered Recurring Patterns ({len(patterns)}):", fg="cyan", bold=True)
    for p in patterns:
        click.echo(f"- [{p.pattern_id}] Recurrence={p.recurrence_count} Conf={p.confidence:.2f}: {p.pattern_summary}")
        if p.known_exceptions:
            click.secho(f"    Exceptions: {', '.join(p.known_exceptions)}", fg="yellow")
    click.echo("")


@memory_cli.command(name="revalidate")
@click.argument("memory_id")
def revalidate_command(memory_id: str) -> None:
    """Mark a memory item as revalidated and freshness to CURRENT."""
    service = get_cognitive_memory_service()
    mem = service.revalidate_memory(memory_id)
    if not mem:
        click.secho(f"Memory '{memory_id}' not found.", fg="red")
        return
    click.secho(f"Memory '{memory_id}' successfully revalidated to CURRENT.", fg="green")


@memory_cli.command(name="invalidate")
@click.argument("memory_id")
@click.option("--reason", default="MANUAL_CLI_INVALIDATION", help="Reason for invalidation")
def invalidate_command(memory_id: str, reason: str) -> None:
    """Retire/invalidate a memory item."""
    service = get_cognitive_memory_service()
    mem = service.invalidate_memory(memory_id, reason=reason)
    if not mem:
        click.secho(f"Memory '{memory_id}' not found.", fg="red")
        return
    click.secho(f"Memory '{memory_id}' successfully invalidated ({reason}).", fg="yellow")


@memory_cli.command(name="snapshot")
def snapshot_command() -> None:
    """Create an immutable point-in-time memory snapshot."""
    service = get_cognitive_memory_service()
    snap = service.create_snapshot()
    click.secho(f"Snapshot created successfully: {snap.snapshot_id}", fg="green", bold=True)
    click.echo(f"Active: {snap.active_count} | Stale: {snap.stale_count} | Conflicts: {snap.conflicted_count} | Patterns: {snap.pattern_count}")


cognitive_memory = memory_cli
cognitive_memory_cli = memory_cli

if __name__ == "__main__":
    memory_cli()
