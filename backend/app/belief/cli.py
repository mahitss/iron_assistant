"""Command-line interface for Task 107:
KAIRO Autonomous Belief, Evidence Arbitration, Conflict Resolution & World-Model Revision Engine.
Implements 'kairo belief' and 'kairo evidence' commands.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Optional

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.belief.domain import (
    BeliefScope,
    BeliefStatus,
    EvidenceClassification,
)
from app.belief.service import BeliefService


def build_belief_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo belief' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("belief", help="Belief, evidence arbitration & world-model revision commands")
    else:
        parser = argparse.ArgumentParser(prog="kairo belief", description="Kairo Belief Engine CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    list_p = sub.add_parser("list", help="List active beliefs")
    list_p.add_argument("--scope", help="Filter by scope")
    list_p.add_argument("--status", choices=[s.value for s in BeliefStatus], help="Filter by status")
    list_p.add_argument("--stale", action="store_true", help="Filter stale beliefs")

    # 2. search
    search_p = sub.add_parser("search", help="Search beliefs by subject or predicate")
    search_p.add_argument("query", help="Search query string")

    # 3. show
    show_p = sub.add_parser("show", help="Show full belief details")
    show_p.add_argument("belief_id", help="Belief ID")

    # 4. evidence
    ev_p = sub.add_parser("evidence", help="Show supporting and contradicting evidence for a belief")
    ev_p.add_argument("belief_id", help="Belief ID")

    # 5. conflicts
    conf_p = sub.add_parser("conflicts", help="Show active conflicts for a belief or system-wide")
    conf_p.add_argument("--belief_id", help="Optional Belief ID")

    # 6. history
    hist_p = sub.add_parser("history", help="Show non-destructive revision history")
    hist_p.add_argument("belief_id", help="Belief ID")

    # 7. dependencies
    dep_p = sub.add_parser("dependencies", help="Show upstream and downstream dependencies")
    dep_p.add_argument("belief_id", help="Belief ID")

    # 8. stale
    sub.add_parser("stale", help="List stale beliefs requiring revalidation")

    # 9. contested
    sub.add_parser("contested", help="List contested beliefs with competing evidence")

    # 10. unknown
    sub.add_parser("unknown", help="List beliefs with unknown or insufficient evidence")

    # 11. snapshot
    snap_p = sub.add_parser("snapshot", help="Capture a point-in-time belief snapshot")
    snap_p.add_argument("--trigger", default="MANUAL", help="Trigger type")
    snap_p.add_argument("--ref", help="Optional reference ID (decision_id, run_id, etc.)")

    # 12. explain
    exp_p = sub.add_parser("explain", help="Provide evidence-based explanation of belief")
    exp_p.add_argument("belief_id", help="Belief ID")

    return parser


def build_evidence_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo evidence' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("evidence", help="Evidence item commands")
    else:
        parser = argparse.ArgumentParser(prog="kairo evidence", description="Kairo Evidence CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    list_p = sub.add_parser("list", help="List ingested evidence items")
    list_p.add_argument("--limit", type=int, default=50)

    # 2. show
    show_p = sub.add_parser("show", help="Show details of an evidence item")
    show_p.add_argument("evidence_id", help="Evidence ID")

    # 3. search
    search_p = sub.add_parser("search", help="Search evidence items by summary")
    search_p.add_argument("query", help="Text search query")

    return parser


def execute_belief_cli(args: argparse.Namespace) -> int:
    service = BeliefService.get_instance()

    if args.subcommand == "list":
        status = BeliefStatus(args.status) if getattr(args, "status", None) else None
        beliefs = service.list_beliefs(scope=getattr(args, "scope", None), status=status, is_stale=getattr(args, "stale", None))
        for b in beliefs:
            stale_str = " [STALE]" if b.is_stale else ""
            print(f"{b.belief_id} | {b.subject}.{b.predicate} | {b.status.value} (conf={b.confidence:.2f}){stale_str}")
        return 0

    elif args.subcommand == "show":
        b = service.get_belief(args.belief_id)
        if not b:
            print(f"Error: Belief '{args.belief_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(b.model_dump(), indent=2, default=str))
        return 0

    elif args.subcommand == "explain":
        try:
            exp = service.explain_belief(args.belief_id)
            print(json.dumps(exp.model_dump(), indent=2, default=str))
            return 0
        except KeyError:
            print(f"Error: Belief '{args.belief_id}' not found.", file=sys.stderr)
            return 1

    elif args.subcommand == "stale":
        beliefs = service.list_beliefs(is_stale=True)
        for b in beliefs:
            print(f"{b.belief_id} | {b.subject}.{b.predicate} | {b.status.value} (TTL={b.freshness_ttl_seconds}s)")
        return 0

    elif args.subcommand == "contested":
        beliefs = service.list_beliefs(status=BeliefStatus.CONTESTED)
        for b in beliefs:
            print(f"{b.belief_id} | {b.subject}.{b.predicate} | CONTESTED (contradictions={len(b.contradiction_evidence_ids)})")
        return 0

    elif args.subcommand == "unknown":
        beliefs = service.list_beliefs(status=BeliefStatus.UNKNOWN)
        for b in beliefs:
            print(f"{b.belief_id} | {b.subject}.{b.predicate} | UNKNOWN")
        return 0

    elif args.subcommand == "snapshot":
        snap = service.capture_snapshot(trigger_type=args.trigger, reference_id=args.ref)
        print(f"Snapshot created: {snap.snapshot_id} (hash={snap.integrity_hash[:12]})")
        return 0

    elif args.subcommand == "conflicts":
        conflicts = service.get_conflicts(getattr(args, "belief_id", None))
        for c in conflicts:
            print(f"Conflict {c.conflict_id} [{c.conflict_type.value}]: {c.rationale} (Resolution: {c.resolution.value})")
        return 0

    print(f"Unknown subcommand '{args.subcommand}'", file=sys.stderr)
    return 1


if __name__ == "__main__":
    parser = build_belief_parser()
    parsed = parser.parse_args()
    sys.exit(execute_belief_cli(parsed))
