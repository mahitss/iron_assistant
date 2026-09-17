"""Command-line interface for Task 108:
KAIRO Autonomous Intent Understanding, Goal Inference, User Alignment & Request Semantics Engine.

Implements CLI commands:
- kairo intent list
- kairo intent search <query>
- kairo intent show <id>
- kairo intent evidence <id>
- kairo intent assumptions <id>
- kairo intent ambiguities <id>
- kairo intent corrections <id>
- kairo intent history <id>
- kairo intent snapshot <id>
- kairo request show <id>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Optional

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.intent.domain import (
    EpistemicStatus,
    IntentCategory,
    RequestStatus,
)
from app.intent.service import IntentService, get_intent_service


def build_intent_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo intent' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("intent", help="Intent understanding & goal inference commands (Task 108)")
    else:
        parser = argparse.ArgumentParser(prog="kairo intent", description="Kairo Intent Understanding CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    list_p = sub.add_parser("list", help="List active structured intents")
    list_p.add_argument("--category", choices=[c.value for c in IntentCategory], help="Filter by category")
    list_p.add_argument("--status", choices=[s.value for s in RequestStatus], help="Filter by status")
    list_p.add_argument("--limit", type=int, default=50, help="Limit results")

    # 2. search
    search_p = sub.add_parser("search", help="Search intents by query")
    search_p.add_argument("query", help="Search text query")

    # 3. show
    show_p = sub.add_parser("show", help="Show details of an intent")
    show_p.add_argument("intent_id", help="Intent ID")

    # 4. evidence
    ev_p = sub.add_parser("evidence", help="Show provenance-backed evidence supporting an intent")
    ev_p.add_argument("intent_id", help="Intent ID")

    # 5. assumptions
    as_p = sub.add_parser("assumptions", help="Show operational assumptions and safe defaults")
    as_p.add_argument("intent_id", help="Intent ID")

    # 6. ambiguities
    amb_p = sub.add_parser("ambiguities", help="Show detected ambiguities and consequences")
    amb_p.add_argument("intent_id", help="Intent ID")

    # 7. corrections
    cor_p = sub.add_parser("corrections", help="Show user corrections applied to an intent")
    cor_p.add_argument("intent_id", help="Intent ID")

    # 8. history
    hist_p = sub.add_parser("history", help="Show immutable revision history for an intent")
    hist_p.add_argument("intent_id", help="Intent ID")

    # 9. snapshot
    snap_p = sub.add_parser("snapshot", help="Inspect decision-time immutable snapshot")
    snap_p.add_argument("intent_id", help="Intent ID")

    return parser


def build_request_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo request' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("request", help="User request inspection commands (Task 108)")
    else:
        parser = argparse.ArgumentParser(prog="kairo request", description="Kairo User Request CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. show
    show_p = sub.add_parser("show", help="Show details of a user request")
    show_p.add_argument("request_id", help="Request ID")

    # 2. list
    list_p = sub.add_parser("list", help="List tracked user requests")
    list_p.add_argument("--limit", type=int, default=50, help="Limit results")

    return parser


def handle_intent_cli(args: argparse.Namespace, service: Optional[IntentService] = None) -> int:
    """Dispatches 'kairo intent' subcommands."""
    svc = service or get_intent_service()

    if args.subcommand == "list":
        intents = svc.list_autonomous_intents(
            category=IntentCategory(args.category) if args.category else None,
            status=RequestStatus(args.status) if args.status else None,
            limit=args.limit,
        )
        data = [
            {
                "intent_id": i.intent_id,
                "category": i.category.value,
                "target": i.target,
                "target_epistemic": i.target_epistemic.value,
                "status": i.status.value,
                "confidence": round(i.overall_confidence, 2),
                "summary": i.summary,
            }
            for i in intents
        ]
        print(json.dumps(data, indent=2))
        return 0

    elif args.subcommand == "search":
        results = svc.search_autonomous_intents(args.query)
        data = [
            {
                "intent_id": i.intent_id,
                "category": i.category.value,
                "target": i.target,
                "status": i.status.value,
                "summary": i.summary,
            }
            for i in results
        ]
        print(json.dumps(data, indent=2))
        return 0

    elif args.subcommand == "show":
        intent = svc.get_autonomous_intent(args.intent_id)
        if not intent:
            print(f"Error: Intent '{args.intent_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(intent.model_dump(mode="json"), indent=2))
        return 0

    elif args.subcommand == "evidence":
        evs = svc.get_intent_evidence(args.intent_id)
        data = [e.model_dump(mode="json") if hasattr(e, "model_dump") else e for e in evs]
        print(json.dumps(data, indent=2))
        return 0

    elif args.subcommand == "assumptions":
        asms = svc._assumptions_map.get(args.intent_id, [])
        data = [a.model_dump(mode="json") for a in asms]
        print(json.dumps(data, indent=2))
        return 0

    elif args.subcommand == "ambiguities":
        ambs = svc._ambiguities_map.get(args.intent_id, [])
        data = [a.model_dump(mode="json") for a in ambs]
        print(json.dumps(data, indent=2))
        return 0

    elif args.subcommand == "corrections":
        corrs = svc.get_intent_corrections(args.intent_id)
        data = [c.model_dump(mode="json") for c in corrs]
        print(json.dumps(data, indent=2))
        return 0

    elif args.subcommand == "history":
        vers = svc.get_intent_versions(args.intent_id)
        data = [v.model_dump(mode="json") for v in vers]
        print(json.dumps(data, indent=2))
        return 0

    elif args.subcommand == "snapshot":
        snap = svc.get_intent_snapshot_record(args.intent_id)
        if not snap:
            print(f"Error: Snapshot for intent '{args.intent_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(snap.model_dump(mode="json"), indent=2))
        return 0

    print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
    return 1


def handle_request_cli(args: argparse.Namespace, service: Optional[IntentService] = None) -> int:
    """Dispatches 'kairo request' subcommands."""
    svc = service or get_intent_service()

    if args.subcommand == "show":
        req = svc.get_user_request(args.request_id)
        if not req:
            print(f"Error: Request '{args.request_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(req.model_dump(mode="json"), indent=2))
        return 0

    elif args.subcommand == "list":
        reqs = svc.list_user_requests(limit=args.limit)
        data = [r.model_dump(mode="json") for r in reqs]
        print(json.dumps(data, indent=2))
        return 0

    print(f"Unknown subcommand: {args.subcommand}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    main_parser = argparse.ArgumentParser(prog="kairo", description="Kairo Intent Engine CLI")
    subparsers = main_parser.add_subparsers(dest="command", required=True)
    build_intent_parser(subparsers)
    build_request_parser(subparsers)

    parsed_args = main_parser.parse_args()
    if parsed_args.command == "intent":
        sys.exit(handle_intent_cli(parsed_args))
    elif parsed_args.command == "request":
        sys.exit(handle_request_cli(parsed_args))
    else:
        main_parser.print_help()
        sys.exit(1)
