"""Command-line interface for Task 106:
KAIRO Autonomous Knowledge-to-Action Learning, Strategy Synthesis & Adaptive Operating Policy Engine.
Implements 'kairo strategy' commands.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Optional

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.strategy.domain import (
    StrategyCategory,
    StrategyStatus,
)
from app.strategy.service import StrategyService


def build_strategy_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo strategy' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("strategy", help="Strategy synthesis & adaptive operating policy commands")
    else:
        parser = argparse.ArgumentParser(prog="kairo strategy", description="Kairo Strategy Engine CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    list_p = sub.add_parser("list", help="List strategies")
    list_p.add_argument("--category", choices=[c.value for c in StrategyCategory], help="Filter by category")
    list_p.add_argument("--status", choices=[s.value for s in StrategyStatus], help="Filter by lifecycle status")
    list_p.add_argument("--stale", action="store_true", help="Filter by stale status")

    # 2. search
    search_p = sub.add_parser("search", help="Search strategies by query")
    search_p.add_argument("query", help="Text search query")

    # 3. show
    show_p = sub.add_parser("show", help="Show full strategy detail")
    show_p.add_argument("strategy_id", help="Strategy ID")

    # 4. versions
    vers_p = sub.add_parser("versions", help="List immutable versions of a strategy")
    vers_p.add_argument("strategy_id", help="Strategy ID")

    # 5. evidence
    evi_p = sub.add_parser("evidence", help="Show evidence and counterexamples for a strategy")
    evi_p.add_argument("strategy_id", help="Strategy ID")

    # 6. applicability
    app_p = sub.add_parser("applicability", help="Evaluate applicability against context JSON")
    app_p.add_argument("strategy_id", help="Strategy ID")
    app_p.add_argument("--context", default="{}", help="Context JSON string")

    # 7. conflicts
    conf_p = sub.add_parser("conflicts", help="Show detected strategy conflicts")
    conf_p.add_argument("strategy_id", nargs="?", help="Optional Strategy ID")

    # 8. coverage
    sub.add_parser("coverage", help="Show strategy coverage by category and domain")

    # 9. feedback
    feed_p = sub.add_parser("feedback", help="Submit execution outcome feedback")
    feed_p.add_argument("strategy_id", help="Strategy ID")
    feed_p.add_argument("--status", choices=["SUCCESS", "FAILURE", "PARTIAL"], default="SUCCESS")
    feed_p.add_argument("--cost", type=float, default=0.0)

    # 10. revalidate
    reval_p = sub.add_parser("revalidate", help="Trigger revalidation for a stale strategy")
    reval_p.add_argument("strategy_id", help="Strategy ID")

    # 11. proposals
    sub.add_parser("proposals", help="List strategy promotion proposals")

    # 12. history
    hist_p = sub.add_parser("history", help="Show strategy usage and execution history")
    hist_p.add_argument("strategy_id", help="Strategy ID")

    return parser


def handle_strategy_cli(args: argparse.Namespace, service: Optional[StrategyService] = None) -> int:
    """Executes the parsed 'kairo strategy' CLI command."""
    svc = service or StrategyService()

    if args.subcommand == "list":
        strats = svc.list_strategies(
            category=StrategyCategory(args.category) if args.category else None,
            status=StrategyStatus(args.status) if args.status else None,
            is_stale=True if args.stale else None,
        )
        print(f"\nStrategies ({len(strats)} total):")
        for s in strats:
            stale_str = " [STALE]" if s.is_stale else ""
            print(f"  [{s.lifecycle_status.value}] {s.id} - {s.name} ({s.category.value}, conf={s.confidence:.2f}){stale_str}")
        return 0

    elif args.subcommand == "show":
        strat = svc.get_strategy(args.strategy_id)
        if not strat:
            print(f"Strategy '{args.strategy_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(strat.model_dump(), indent=2, default=str))
        return 0

    elif args.subcommand == "versions":
        strat = svc.get_strategy(args.strategy_id)
        if not strat:
            print(f"Strategy '{args.strategy_id}' not found.", file=sys.stderr)
            return 1
        print(f"\nVersion History for Strategy {strat.id}:")
        for v in strat.versions:
            print(f"  v{v.version_number} [{v.id}]: {v.change_reason} (conf={v.confidence:.2f}, rules={len(v.rules)})")
        return 0

    elif args.subcommand == "evidence":
        strat = svc.get_strategy(args.strategy_id)
        if not strat:
            print(f"Strategy '{args.strategy_id}' not found.", file=sys.stderr)
            return 1
        print(f"\nEvidence for Strategy {strat.id} ({len(strat.evidences)} supporting, {len(strat.counterexamples)} counterexamples):")
        for e in strat.evidences:
            print(f"  [+] {e.source_type.value}: {e.claim} (weight={e.confidence_weight})")
        for c in strat.counterexamples:
            print(f"  [-] EXCEPTION: {c.claim} (ctx={c.environmental_context})")
        return 0

    elif args.subcommand == "applicability":
        ctx = json.loads(args.context)
        app = svc.evaluate_strategy_applicability(args.strategy_id, ctx)
        print(f"\nApplicability for Strategy {args.strategy_id}:")
        print(f"  Status: {app.applicability_status.value} (score={app.applicability_score:.2f})")
        if app.blocking_reasons:
            print(f"  Blocking Reasons: {app.blocking_reasons}")
        if app.uncertainty_reasons:
            print(f"  Uncertainty Reasons: {app.uncertainty_reasons}")
        return 0

    elif args.subcommand == "coverage":
        dash = svc.get_dashboard()
        print(f"\nStrategy Coverage by Category ({dash.total_strategies} total):")
        for cat, count in dash.coverage_by_category.items():
            print(f"  {cat:20s}: {count}")
        return 0

    elif args.subcommand == "revalidate":
        strat = svc.revalidate_strategy(args.strategy_id)
        print(f"Strategy {strat.id} marked VALIDATING. Last validated reset to now.")
        return 0

    elif args.subcommand == "proposals":
        props = list(svc._proposals.values())
        print(f"\nStrategy Proposals ({len(props)} total):")
        for p in props:
            print(f"  [{p.status.value}] {p.id}: {p.proposal_title} (target_v={p.target_version})")
        return 0

    else:
        print(f"Subcommand '{args.subcommand}' not fully handled.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    parser = build_strategy_parser()
    sys.exit(handle_strategy_cli(parser.parse_args()))
