"""CLI subcommands for Task 115 (Section 57):
Autonomous Hypothesis Management, Competing Explanations, Evidence Update, Falsification & Uncertainty Resolution Engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from app.hypothesis.service import get_hypothesis_service


def main(args_list: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="kairo hypothesis",
        description="Autonomous Hypothesis Management & Competing Explanations Engine CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Hypothesis subcommands")

    # 1. create
    create_parser = subparsers.add_parser("create", help="Create a competing hypothesis set or hypothesis")
    create_parser.add_argument("target", help="Target incident or explanation subject")
    create_parser.add_argument("--set-id", default=None, help="Existing set ID if adding a hypothesis")
    create_parser.add_argument("--statement", default=None, help="Specific hypothesis statement")

    # 2. list
    list_parser = subparsers.add_parser("list", help="List active hypotheses or sets")
    list_parser.add_argument("--set-id", default=None, help="Filter by set ID")

    # 3. show <id>
    show_parser = subparsers.add_parser("show", help="Show hypothesis details")
    show_parser.add_argument("id", help="Hypothesis ID")

    # 4. evidence <id>
    evi_parser = subparsers.add_parser("evidence", help="Show evidence for hypothesis")
    evi_parser.add_argument("id", help="Hypothesis ID")

    # 5. predictions <id>
    pred_parser = subparsers.add_parser("predictions", help="Show predictions and calibration")
    pred_parser.add_argument("id", help="Hypothesis ID")

    # 6. falsification <id>
    fals_parser = subparsers.add_parser("falsification", help="Show testable falsification conditions")
    fals_parser.add_argument("id", help="Hypothesis ID")

    # 7. alternatives <id>
    alt_parser = subparsers.add_parser("alternatives", help="List competing alternatives for target")
    alt_parser.add_argument("id", help="Hypothesis ID")

    # 8. conflicts <id>
    conf_parser = subparsers.add_parser("conflicts", help="Show conflicts involving hypothesis")
    conf_parser.add_argument("id", help="Hypothesis ID")

    # 9. compare <set-id>
    comp_parser = subparsers.add_parser("compare", help="Side-by-side comparison of competing hypotheses")
    comp_parser.add_argument("set_id", help="Hypothesis Set ID")

    # 10. evaluate <id>
    eval_parser = subparsers.add_parser("evaluate", help="Re-evaluate confidence and bias guards")
    eval_parser.add_argument("id", help="Hypothesis ID")

    # 11. verify <id>
    veri_parser = subparsers.add_parser("verify", help="Evaluate if hypothesis meets strict verification invariants")
    veri_parser.add_argument("id", help="Hypothesis ID")

    # 12. snapshot <id>
    snap_parser = subparsers.add_parser("snapshot", help="Capture snapshot of hypothesis set")
    snap_parser.add_argument("id", help="Hypothesis ID or Set ID")

    args = parser.parse_args(args_list)
    svc = get_hypothesis_service()

    if args.subcommand == "create":
        if args.set_id:
            hyp = svc.add_hypothesis_to_set(
                args.set_id,
                {"statement": args.statement or args.target, "provenance": "USER_PROVIDED"},
            )
            print(f"Created hypothesis '{hyp.hypothesis_id}' in set '{args.set_id}'.")
            print(json.dumps(hyp.to_dict(), indent=2))
        else:
            hset = svc.create_hypothesis_set(target_description=args.target)
            print(f"Created hypothesis set '{hset.set_id}' with {len(hset.active_hypothesis_ids)} hypotheses.")
            print(json.dumps(hset.to_dict(), indent=2))

    elif args.subcommand == "list":
        if args.set_id:
            hyps = svc.list_hypotheses(args.set_id)
            print(json.dumps([h.to_dict() for h in hyps], indent=2))
        else:
            sets = svc.list_hypothesis_sets()
            print(json.dumps([s.to_dict() for s in sets], indent=2))

    elif args.subcommand == "show":
        hyp = svc.get_hypothesis(args.id)
        if not hyp:
            print(f"Error: Hypothesis '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(hyp.to_dict(), indent=2))

    elif args.subcommand == "evidence":
        hyp = svc.get_hypothesis(args.id)
        if not hyp:
            print(f"Error: Hypothesis '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps({
            "hypothesis_id": hyp.hypothesis_id,
            "supporting_evidence_ids": hyp.supporting_evidence_ids,
            "contradicting_evidence_ids": hyp.contradicting_evidence_ids,
            "falsifying_evidence_ids": hyp.falsifying_evidence_ids,
            "assessments": [a.to_dict() for a in hyp.assessments],
        }, indent=2))

    elif args.subcommand == "predictions":
        hyp = svc.get_hypothesis(args.id)
        if not hyp:
            print(f"Error: Hypothesis '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([p.to_dict() for p in hyp.predictions], indent=2))

    elif args.subcommand == "falsification":
        hyp = svc.get_hypothesis(args.id)
        if not hyp:
            print(f"Error: Hypothesis '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([f.to_dict() for f in hyp.falsification_conditions], indent=2))

    elif args.subcommand == "alternatives":
        hyp = svc.get_hypothesis(args.id)
        if not hyp:
            print(f"Error: Hypothesis '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        all_hyps = svc.list_hypotheses(hyp.set_id)
        alts = [h.to_dict() for h in all_hyps if h.hypothesis_id != args.id]
        print(json.dumps(alts, indent=2))

    elif args.subcommand == "conflicts":
        hyp = svc.get_hypothesis(args.id)
        if not hyp:
            print(f"Error: Hypothesis '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        hset = svc.get_hypothesis_set(hyp.set_id)
        confs = []
        if hset:
            confs = [c.to_dict() for c in hset.unresolved_conflicts if c.hypothesis_a_id == args.id or c.hypothesis_b_id == args.id]
        print(json.dumps(confs, indent=2))

    elif args.subcommand == "compare":
        try:
            matrix = svc.get_side_by_side_comparison(args.set_id)
            print(json.dumps(matrix, indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.subcommand == "evaluate":
        hyp = svc.get_hypothesis(args.id)
        if not hyp:
            print(f"Error: Hypothesis '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        hset = svc.get_hypothesis_set(hyp.set_id)
        if hset:
            svc.bias_guard_engine.check_and_apply_safeguards(hyp, hset, svc.list_hypotheses(hyp.set_id), list(svc._evidence.values()))
        print(json.dumps(hyp.to_dict(), indent=2))

    elif args.subcommand == "verify":
        try:
            res = svc.verify_hypothesis(args.id)
            print(json.dumps(res, indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.subcommand == "snapshot":
        hyp = svc.get_hypothesis(args.id)
        set_id = hyp.set_id if hyp else args.id
        try:
            snap = svc.create_snapshot(set_id)
            print(json.dumps(snap.to_dict(), indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
