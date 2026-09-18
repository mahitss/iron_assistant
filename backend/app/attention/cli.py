"""Command-line interface for Task 109:
KAIRO Autonomous Attention, Cognitive Resource Allocation, Focus Management & Interruption Governance Engine.

Implements CLI commands:
- kairo attention list [--lifecycle] [--type] [--limit]
- kairo attention show <candidate_id>
- kairo attention focus
- kairo attention health
- kairo attention watches
- kairo attention snapshot
- kairo attention sweep
- kairo attention ingest --source ... --title ... [--urgency] [--importance] [--risk]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Optional

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.attention.domain import (
    AttentionCandidate,
    AttentionCandidateType,
    AttentionLifecycleState,
    FocusTarget,
)
from app.attention.service import AttentionEngineService


def build_attention_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo attention' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("attention", help="Autonomous Attention & Focus commands (Task 109)")
    else:
        parser = argparse.ArgumentParser(prog="kairo attention", description="Kairo Attention Engine CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    list_p = sub.add_parser("list", help="List attention candidates ordered by salience")
    list_p.add_argument("--lifecycle", choices=[s.value for s in AttentionLifecycleState], help="Filter by lifecycle")
    list_p.add_argument("--type", choices=[t.value for t in AttentionCandidateType], help="Filter by type")
    list_p.add_argument("--limit", type=int, default=50, help="Limit results")

    # 2. show
    show_p = sub.add_parser("show", help="Show full details of an attention candidate")
    show_p.add_argument("candidate_id", help="Candidate ID")

    # 3. focus
    sub.add_parser("focus", help="Show active focus session and nested attention stack")

    # 4. health
    sub.add_parser("health", help="Display cognitive health status, churn, and fragmentation metrics")

    # 5. watches
    sub.add_parser("watches", help="List active zero-cost condition watches")

    # 6. snapshot
    sub.add_parser("snapshot", help="Capture and print immutable point-in-time attention snapshot")

    # 7. sweep
    sub.add_parser("sweep", help="Run fairness aging sweep across queued items to prevent starvation")

    # 8. ingest
    ingest_p = sub.add_parser("ingest", help="Ingest a stimulus into an attention candidate")
    ingest_p.add_argument("--source", required=True, help="Stimulus source")
    ingest_p.add_argument("--title", required=True, help="Candidate title")
    ingest_p.add_argument("--description", default="", help="Candidate description")
    ingest_p.add_argument("--type", default="USER_REQUEST", choices=[t.value for t in AttentionCandidateType], help="Type")
    ingest_p.add_argument("--urgency", type=float, default=0.5, help="Urgency (0.0-1.0)")
    ingest_p.add_argument("--importance", type=float, default=0.5, help="Importance (0.0-1.0)")
    ingest_p.add_argument("--risk", type=float, default=0.3, help="Risk (0.0-1.0)")

    return parser


def handle_attention_cli(args: argparse.Namespace) -> int:
    """Executes the attention CLI commands."""
    service = AttentionEngineService.get_instance()

    if args.subcommand == "list":
        lifecycle = AttentionLifecycleState(args.lifecycle) if args.lifecycle else None
        cand_type = AttentionCandidateType(args.type) if args.type else None
        candidates = service.list_candidates_t109(lifecycle=lifecycle, candidate_type=cand_type, limit=args.limit)
        print(f"Total candidates: {len(candidates)}")
        for c in candidates:
            print(f"- [{c.lifecycle.value}] [{c.score.composite_salience:.2f}] {c.candidate_id}: {c.title} (type={c.type.value})")
        return 0

    elif args.subcommand == "show":
        cand = service.get_candidate_t109(args.candidate_id)
        if not cand:
            print(f"Error: Candidate '{args.candidate_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(cand.model_dump(), indent=2, default=str))
        return 0

    elif args.subcommand == "focus":
        active = service.focus_mgr.active_session
        stack = service.focus_mgr.stack
        print("=== Active Focus Session ===")
        if active:
            print(f"Session ID: {active.session_id}")
            print(f"Candidate ID: {active.candidate_id}")
            print(f"Target: {active.primary_target.name} ({active.primary_target.target_id})")
            print(f"Depth: {active.depth}")
            print(f"Started: {active.started_at}")
        else:
            print("No active focus session (IDLE).")

        print(f"\n=== Stack Depth: {len(stack)} ===")
        for s in reversed(stack):
            print(f"- [Depth {s.depth}] {s.session_id}: {s.primary_target.name} (Candidate: {s.candidate_id})")
        return 0

    elif args.subcommand == "health":
        health = service.get_health_status_t109()
        print("=== Cognitive Health & Stability Status ===")
        for k, v in health.items():
            print(f"{k}: {v}")
        return 0

    elif args.subcommand == "watches":
        watches = list(service.watches_reminders.watches.values())
        print(f"=== Active Condition Watches: {len(watches)} ===")
        for w in watches:
            active_str = "ACTIVE" if w.is_active else "TRIGGERED"
            print(f"- [{active_str}] {w.watch_id} (Cand: {w.candidate_id}): {w.condition_type.value} -> '{w.condition_expr}'")
        return 0

    elif args.subcommand == "snapshot":
        snap = service.capture_snapshot_t109()
        print(json.dumps(snap.model_dump(), indent=2, default=str))
        return 0

    elif args.subcommand == "sweep":
        aged = service.run_fairness_sweep_t109()
        print(f"Fairness sweep complete. Aged {len(aged)} queued/deferred candidates.")
        for c in aged:
            print(f"- {c.candidate_id}: aging_boost={c.aging_boost:.3f}, composite_salience={c.score.composite_salience:.2f}")
        return 0

    elif args.subcommand == "ingest":
        cand = AttentionCandidate(
            source=args.source,
            type=AttentionCandidateType(args.type),
            title=args.title,
            description=args.description,
        )
        cand.score.urgency = args.urgency
        cand.score.importance = args.importance
        cand.score.risk = args.risk
        ingested = service.ingest_candidate_t109(cand)
        print(f"Ingested candidate: {ingested.candidate_id}")
        print(f"Salience: {ingested.score.composite_salience:.2f} (Urgency: {ingested.score.urgency:.2f}, Risk: {ingested.score.risk:.2f})")
        return 0

    return 0


def main() -> None:
    parser = build_attention_parser()
    args = parser.parse_args()
    sys.exit(handle_attention_cli(args))


if __name__ == "__main__":
    main()
