"""Command-line interface for KAIRO System State Graph, Self-Modeling & Operational Digital Twin (Task 93 Phase 29).

Usage:
  kairo-system status
  kairo-system health
  kairo-system graph
  kairo-system diagnostics
  kairo-system self-model
  kairo-system changes [--limit <N>]
  kairo-system snapshot [--watermark <W>]
  kairo-system reconcile
  kairo-system impact <component_id>
  kairo-system dependents <component_id>
  kairo-system dependencies <component_id>
  kairo-system goal <goal_id>
  kairo-system task <task_id>
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.system_state.service import get_system_state_service


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for system-state commands."""
    parser = argparse.ArgumentParser(
        prog="kairo-system",
        description="Kairo Autonomous System State Graph & Operational Digital Twin CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # status
    subparsers.add_parser("status", help="Show high-level system state summary")

    # health
    subparsers.add_parser("health", help="Show operational health and degraded components")

    # graph
    subparsers.add_parser("graph", help="Display operational graph topology summary")

    # diagnostics
    subparsers.add_parser("diagnostics", help="Generate structured system self-diagnostics")

    # self-model
    subparsers.add_parser("self-model", help="Query Kairo's operational self-model questions")

    # changes
    p_changes = subparsers.add_parser("changes", help="View recent operational state deltas")
    p_changes.add_argument("--limit", type=int, default=20, help="Number of deltas to show")

    # snapshot
    p_snap = subparsers.add_parser("snapshot", help="Create an immutable state snapshot")
    p_snap.add_argument("--watermark", type=int, default=None, help="Event watermark")

    # reconcile
    subparsers.add_parser("reconcile", help="Trigger startup state reconciliation")

    # impact
    p_impact = subparsers.add_parser("impact", help="Query downstream impact of a component")
    p_impact.add_argument("component_id", help="Component ID to inspect")

    # dependents
    p_dep = subparsers.add_parser("dependents", help="Query upstream dependents of a component")
    p_dep.add_argument("component_id", help="Component ID to inspect")

    # dependencies
    p_deps = subparsers.add_parser("dependencies", help="Query upstream dependencies of a component")
    p_deps.add_argument("component_id", help="Component ID to inspect")

    # goal
    p_goal = subparsers.add_parser("goal", help="Inspect operational state of a goal")
    p_goal.add_argument("goal_id", help="Goal ID to inspect")

    # task
    p_task = subparsers.add_parser("task", help="Inspect operational state of a task")
    p_task.add_argument("task_id", help="Task ID to inspect")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI execution entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    service = get_system_state_service()

    try:
        if args.subcommand == "status":
            summary = service.get_summary()
            print(json.dumps(summary, indent=2))

        elif args.subcommand == "health":
            health = service.get_health()
            print(json.dumps(health, indent=2))

        elif args.subcommand == "graph":
            data = service.get_graph_data()
            print(json.dumps({"nodes_count": len(data["nodes"]), "links_count": len(data["links"])}, indent=2))

        elif args.subcommand == "diagnostics":
            diag = service.get_diagnostics()
            print(json.dumps(diag.model_dump(mode="json"), indent=2))

        elif args.subcommand == "self-model":
            answers = service.get_self_model_answers()
            print(json.dumps(answers.model_dump(mode="json"), indent=2))

        elif args.subcommand == "changes":
            deltas = service.get_recent_deltas(limit=args.limit)
            print(json.dumps([d.model_dump(mode="json") for d in deltas], indent=2))

        elif args.subcommand == "snapshot":
            snap = service.create_snapshot(watermark=args.watermark)
            print(json.dumps(snap.model_dump(mode="json"), indent=2))

        elif args.subcommand == "reconcile":
            rec = service.reconcile()
            print(json.dumps(rec, indent=2))

        elif args.subcommand == "impact":
            res = service.query_impact(args.component_id)
            print(json.dumps(res, indent=2))

        elif args.subcommand == "dependents":
            res = service.query_dependents(args.component_id)
            print(json.dumps(res, indent=2))

        elif args.subcommand == "dependencies":
            deps = service.graph.dependencies_of(args.component_id)
            print(json.dumps([d.model_dump(mode="json") for d in deps], indent=2))

        elif args.subcommand == "goal":
            res = service.query_goal(args.goal_id)
            print(json.dumps(res, indent=2))

        elif args.subcommand == "task":
            res = service.query_task(args.task_id)
            print(json.dumps(res, indent=2))

        return 0
    except Exception as ex:
        print(f"Error executing kairo-system {args.subcommand}: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
