"""CLI interface for Kairo Autonomous Knowledge Graph Reasoning & Relationship Intelligence (Task 97).

Usage:
    python -m backend.app.knowledge_graph.cli graph inspect <id>
    python -m backend.app.knowledge_graph.cli graph neighbors <id>
    python -m backend.app.knowledge_graph.cli graph dependencies <id>
    python -m backend.app.knowledge_graph.cli graph dependents <id>
    python -m backend.app.knowledge_graph.cli graph lineage <id>
    python -m backend.app.knowledge_graph.cli graph impact <id>
    python -m backend.app.knowledge_graph.cli graph path <a> <b>
    python -m backend.app.knowledge_graph.cli graph history <id>
    python -m backend.app.knowledge_graph.cli graph diff <snapshot_a> <snapshot_b>
    python -m backend.app.knowledge_graph.cli graph validate
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.knowledge_graph.reasoning_engine import get_graph_reasoning_engine
from app.knowledge_graph.schemas import (
    GraphQueryType,
    GraphTraversalLimits,
    NodeType,
    RelationshipType,
    ScopeType,
)


def format_table(headers: list[str], rows: list[list[Any]], max_width: int = 35) -> str:
    if not rows:
        return "No items found."
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            str_val = str(val) if val is not None else ""
            if len(str_val) > max_width:
                str_val = str_val[:max_width - 3] + "..."
            widths[i] = max(widths[i], len(str_val))

    header_line = " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * widths[i] for i in range(len(headers)))
    row_lines = [
        " | ".join((str(val) if val is not None else "")[:widths[i]].ljust(widths[i]) for i, val in enumerate(row))
        for row in rows
    ]
    return f"\n{header_line}\n{sep_line}\n" + "\n".join(row_lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairo-graph",
        description="Kairo Autonomous Knowledge Graph Reasoning & Relationship Intelligence CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subsystem commands")

    # graph subcommands
    graph_parser = subparsers.add_parser("graph", help="Knowledge Graph inspection and reasoning commands")
    graph_subs = graph_parser.add_subparsers(dest="action", help="Graph action to perform")

    # graph inspect <id>
    inspect_cmd = graph_subs.add_parser("inspect", help="Inspect detailed attributes of a knowledge node")
    inspect_cmd.add_argument("node_id", help="Node ID or canonical name to inspect")

    # graph neighbors <id>
    neighbors_cmd = graph_subs.add_parser("neighbors", help="List direct 1-hop neighbors of a node")
    neighbors_cmd.add_argument("node_id", help="Target node ID")

    # graph dependencies <id>
    deps_cmd = graph_subs.add_parser("dependencies", help="Inspect all entities that node depends on and vice-versa")
    deps_cmd.add_argument("node_id", help="Target node ID")
    deps_cmd.add_argument("--depth", type=int, default=4, help="Maximum traversal depth")

    # graph dependents <id>
    dependents_cmd = graph_subs.add_parser("dependents", help="List entities that depend on this node")
    dependents_cmd.add_argument("node_id", help="Target node ID")

    # graph lineage <id>
    lineage_cmd = graph_subs.add_parser("lineage", help="Reconstruct complete operational lineage")
    lineage_cmd.add_argument("node_id", help="Target node ID (Decision, Action, Memory, Agent)")

    # graph impact <id>
    impact_cmd = graph_subs.add_parser("impact", help="Analyze downstream systems affected by a change/failure")
    impact_cmd.add_argument("node_id", help="Target node ID")
    impact_cmd.add_argument("--depth", type=int, default=5, help="Maximum impact depth")

    # graph path <a> <b>
    path_cmd = graph_subs.add_parser("path", help="Find shortest verified relationship path between two nodes")
    path_cmd.add_argument("start_node_id", help="Source node ID")
    path_cmd.add_argument("target_node_id", help="Destination node ID")
    path_cmd.add_argument("--min-confidence", type=float, default=0.5, help="Minimum confidence threshold")

    # graph history <id>
    hist_cmd = graph_subs.add_parser("history", help="Inspect version and merge history of a node")
    hist_cmd.add_argument("node_id", help="Target node ID")

    # graph diff <snapshot_a> <snapshot_b>
    diff_cmd = graph_subs.add_parser("diff", help="Compute structural diff between two graph snapshots")
    diff_cmd.add_argument("snapshot_a_id", help="First snapshot ID")
    diff_cmd.add_argument("snapshot_b_id", help="Second snapshot ID")

    # graph validate
    graph_subs.add_parser("validate", help="Validate graph referential integrity and check for contradictory cycles")

    args = parser.parse_args()

    if not args.subcommand or args.subcommand != "graph" or not args.action:
        parser.print_help()
        sys.exit(1)

    engine = get_graph_reasoning_engine()

    try:
        if args.action == "inspect":
            node = engine.nodes.get_node(args.node_id) or engine.nodes.get_node_by_name(args.node_id)
            if not node:
                print(f"Error: Node '{args.node_id}' not found.")
                sys.exit(1)
            print(f"\nNODE DETAILS: {node.canonical_name} ({node.node_id})")
            print("-" * 60)
            print(f"Type:        {node.node_type.value}")
            print(f"Scope:       {node.scope.value}")
            print(f"Confidence:  {node.confidence:.2f}")
            print(f"Certainty:   {node.certainty.value}")
            print(f"Version:     {node.version}")
            print(f"Status:      {node.status}")
            print(f"Created At:  {node.created_at.isoformat()}")
            print(f"Aliases:     {', '.join(node.aliases) if node.aliases else 'None'}")
            print(f"Metadata:    {json.dumps(node.metadata, indent=2)}")

        elif args.action == "neighbors":
            res = engine.execute_query(
                query_type=GraphQueryType.ONE_HOP,
                start_node_id=args.node_id,
                limits=GraphTraversalLimits(max_depth=1),
            )
            print(f"\nDirect neighbors of node '{args.node_id}':")
            rows = [[n.node_id, n.canonical_name, n.node_type.value, n.confidence] for n in res.nodes if n.node_id != args.node_id]
            print(format_table(["NODE ID", "NAME", "TYPE", "CONFIDENCE"], rows))

        elif args.action == "dependencies":
            res = engine.get_dependencies(node_id=args.node_id, max_depth=args.depth)
            print(f"\nDependency graph for node '{args.node_id}':")
            rows = [[e.source_node_id, e.relationship.value, e.target_node_id, e.confidence] for e in res.edges]
            print(format_table(["SOURCE", "RELATIONSHIP", "TARGET", "CONFIDENCE"], rows))

        elif args.action == "dependents":
            deps = engine.get_dependencies(node_id=args.node_id)
            dependent_ids = {e.source_node_id for e in deps.edges if e.target_node_id == args.node_id}
            dependents = [n for n in deps.nodes if n.node_id in dependent_ids]
            print(f"\nEntities that depend on '{args.node_id}':")
            rows = [[n.node_id, n.canonical_name, n.node_type.value] for n in dependents]
            print(format_table(["NODE ID", "NAME", "TYPE"], rows))

        elif args.action == "lineage":
            node = engine.nodes.get_node(args.node_id)
            if not node:
                print(f"Error: Node '{args.node_id}' not found.")
                sys.exit(1)

            if node.node_type == NodeType.DECISION:
                lin = engine.reconstruct_decision_lineage(args.node_id)
            elif node.node_type == NodeType.ACTION:
                lin = engine.reconstruct_action_lineage(args.node_id)
            elif node.node_type == NodeType.MEMORY:
                lin = engine.reconstruct_memory_lineage(args.node_id)
            elif node.node_type == NodeType.AGENT:
                lin = engine.reconstruct_agent_lineage(args.node_id)
            else:
                lin = engine.reconstruct_decision_lineage(args.node_id)

            print(f"\nOperational Lineage for [{lin.lineage_type}] '{args.node_id}':")
            for i, step in enumerate(lin.steps, 1):
                print(f"  {i}. [{step.get('step')}] {step.get('name')} ({step.get('node_id')})")
            print(f"Complete: {lin.is_complete}")

        elif args.action == "impact":
            impact = engine.analyze_downstream_impact(root_node_id=args.node_id, limits=GraphTraversalLimits(max_depth=args.depth))
            print(f"\nDOWNSTREAM IMPACT ANALYSIS: '{args.node_id}'")
            print("-" * 60)
            print(f"Criticality:    {impact.risk_criticality}")
            print(f"Total Affected: {impact.total_affected}")
            print(f"Max Depth:      {impact.depth}")
            print(f"Summary:        {impact.summary}\n")
            rows = [[n["node_id"], n["canonical_name"], n["node_type"], n["depth"], n["relationship"]] for n in impact.impacted_nodes]
            print(format_table(["NODE ID", "NAME", "TYPE", "DEPTH", "TRIGGER RELATION"], rows))

        elif args.action == "path":
            res = engine.find_shortest_verified_path(
                start_node_id=args.start_node_id,
                target_node_id=args.target_node_id,
                min_confidence=args.min_confidence,
            )
            if not res.edges:
                print(f"No verified path found between '{args.start_node_id}' and '{args.target_node_id}'.")
                sys.exit(0)
            print(f"\nShortest Verified Path (Confidence: {res.path_confidence:.2f}):")
            for i, edge in enumerate(res.edges, 1):
                src = engine.nodes.get_node(edge.source_node_id)
                tgt = engine.nodes.get_node(edge.target_node_id)
                src_name = src.canonical_name if src else edge.source_node_id
                tgt_name = tgt.canonical_name if tgt else edge.target_node_id
                print(f"  {i}. {src_name} --[{edge.relationship.value}]--> {tgt_name} (conf: {edge.confidence:.2f})")

        elif args.action == "history":
            node = engine.nodes.get_node(args.node_id)
            if not node:
                print(f"Error: Node '{args.node_id}' not found.")
                sys.exit(1)
            print(f"\nNode History for '{node.canonical_name}':")
            print(f"Version:     {node.version}")
            print(f"Created:     {node.created_at.isoformat()}")
            print(f"Updated:     {node.updated_at.isoformat()}")
            merges = node.metadata.get("merge_history", [])
            print(f"Merges:      {len(merges)}")
            for m in merges:
                print(f"  - Merged {m.get('merged_node_id')} on {m.get('merged_at')}: {m.get('reason')}")

        elif args.action == "diff":
            diff = engine.compute_graph_diff(args.snapshot_a_id, args.snapshot_b_id)
            print(f"\nGRAPH SNAPSHOT DELTA: {args.snapshot_a_id} -> {args.snapshot_b_id}")
            print("-" * 60)
            print(f"Added Nodes:   {len(diff.added_nodes)} {diff.added_nodes}")
            print(f"Removed Nodes: {len(diff.removed_nodes)} {diff.removed_nodes}")
            print(f"Changed Nodes: {len(diff.changed_nodes)} {diff.changed_nodes}")
            print(f"Added Edges:   {len(diff.added_edges)}")
            print(f"Removed Edges: {len(diff.removed_edges)}")

        elif args.action == "validate":
            orphans = [e.edge_id for e in engine.edges._edges.values() if not engine.nodes.get_node(e.source_node_id)]
            broken_targets = [e.edge_id for e in engine.edges._edges.values() if not engine.nodes.get_node(e.target_node_id)]
            conflicts = engine.list_conflicts(unresolved_only=True)
            print("\nKNOWLEDGE GRAPH INTEGRITY VALIDATION")
            print("-" * 60)
            print(f"Total Nodes:          {len(engine.nodes._nodes)}")
            print(f"Total Edges:          {len(engine.edges._edges)}")
            print(f"Orphan Edges:         {len(orphans)}")
            print(f"Broken Target Edges:  {len(broken_targets)}")
            print(f"Active Conflicts:     {len(conflicts)}")
            if not orphans and not broken_targets:
                print("\n[OK] Graph referential consistency verified.")
            else:
                print("\n[FAIL] Referential integrity violations detected.")

    except Exception as exc:
        print(f"Execution Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
