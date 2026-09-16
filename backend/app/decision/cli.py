"""Command-line interface for KAIRO Autonomous Decision Intelligence & Memory (Task 94 Phase 34).

Usage:
  kairo-decision list [--limit <N>]
  kairo-decision inspect <id>
  kairo-decision options <id>
  kairo-decision explain <id>
  kairo-decision select <id> <option_id> [--actor <ACTOR>]
  kairo-decision re-evaluate <id> [--reason <REASON>]
  kairo-decision outcome <id>
"""

from __future__ import annotations

import argparse
import json
import sys

from app.decision.intelligence_service import get_decision_intelligence_service


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for decision intelligence CLI."""
    parser = argparse.ArgumentParser(
        prog="kairo-decision",
        description="Kairo Autonomous Decision Intelligence & Decision Memory CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List recent decisions")
    p_list.add_argument("--limit", type=int, default=20, help="Number of records to return")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect complete decision record")
    p_inspect.add_argument("decision_id", help="Target decision ID")

    # options
    p_opts = subparsers.add_parser("options", help="List evaluated candidate options and trade-offs")
    p_opts.add_argument("decision_id", help="Target decision ID")

    # explain
    p_explain = subparsers.add_parser("explain", help="Generate structured 15-part evidence-based explanation")
    p_explain.add_argument("decision_id", help="Target decision ID")

    # select
    p_select = subparsers.add_parser("select", help="Explicitly select an option")
    p_select.add_argument("decision_id", help="Target decision ID")
    p_select.add_argument("option_id", help="Target option ID to select")
    p_select.add_argument("--actor", default="operator", help="Actor initiating selection")

    # re-evaluate
    p_reeval = subparsers.add_parser("re-evaluate", help="Trigger re-evaluation following environment drift")
    p_reeval.add_argument("decision_id", help="Target decision ID")
    p_reeval.add_argument("--reason", default="Context drift", help="Reason for re-evaluation")

    # outcome
    p_out = subparsers.add_parser("outcome", help="View verified post-execution outcome")
    p_out.add_argument("decision_id", help="Target decision ID")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint execution."""
    parser = build_parser()
    args = parser.parse_args(argv)
    service = get_decision_intelligence_service()

    try:
        if args.subcommand == "list":
            records = service.list_decisions(limit=args.limit)
            print(json.dumps([r.model_dump(mode="json") for r in records], indent=2))

        elif args.subcommand == "inspect":
            rec = service.get_decision(args.decision_id)
            if not rec:
                print(f"Error: Decision '{args.decision_id}' not found", file=sys.stderr)
                return 1
            print(json.dumps(rec.model_dump(mode="json"), indent=2))

        elif args.subcommand == "options":
            opts = service.get_options(args.decision_id)
            print(json.dumps([o.model_dump(mode="json") for o in opts], indent=2))

        elif args.subcommand == "explain":
            explanation = service.generate_explanation(args.decision_id)
            print(json.dumps(explanation.model_dump(mode="json"), indent=2))

        elif args.subcommand == "select":
            updated = service.select_option(args.decision_id, args.option_id, actor=args.actor)
            print(json.dumps(updated.model_dump(mode="json"), indent=2))

        elif args.subcommand == "re-evaluate":
            updated = service.re_evaluate_decision(args.decision_id, reason=args.reason)
            print(json.dumps(updated.model_dump(mode="json"), indent=2))

        elif args.subcommand == "outcome":
            out = service.get_outcome(args.decision_id)
            if not out:
                print(f"No outcome recorded yet for decision '{args.decision_id}'")
            else:
                print(json.dumps(out.model_dump(mode="json"), indent=2))

        return 0
    except Exception as ex:
        print(f"Error executing kairo-decision {args.subcommand}: {ex}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
