"""Command-line interface for Task 112:
KAIRO Autonomous Causal Explanation, Event Chain Reconstruction & "Why Did This Happen?" Engine.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.causal.explanation.domain import ExplanationRequest
from app.causal.explanation.service import CausalExplanationService


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairo-explain",
        description="Kairo Autonomous Causal Explanation & 'Why Did This Happen?' CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available explanation subcommands")

    # 1. target <entity>
    p_target = subparsers.add_parser("target", help="Explain an entity or incident target")
    p_target.add_argument("entity", help="Target entity or incident identifier")
    p_target.add_argument("--symptom", default=None, help="Specific observed symptom or state change")

    # 2. timeline <id>
    p_timeline = subparsers.add_parser("timeline", help="Inspect event chain timeline for explanation")
    p_timeline.add_argument("id", help="Explanation ID")

    # 3. chain <id>
    p_chain = subparsers.add_parser("chain", help="Inspect causal link chain and mechanisms")
    p_chain.add_argument("id", help="Explanation ID")

    # 4. evidence <id>
    p_evid = subparsers.add_parser("evidence", help="Inspect supporting and contradicting evidence")
    p_evid.add_argument("id", help="Explanation ID")

    # 5. alternatives <id>
    p_alts = subparsers.add_parser("alternatives", help="Inspect competing alternative hypotheses")
    p_alts.add_argument("id", help="Explanation ID")

    # 6. gaps <id>
    p_gaps = subparsers.add_parser("gaps", help="Inspect unresolved causal gaps and telemetry uncertainties")
    p_gaps.add_argument("id", help="Explanation ID")

    # 7. verify <id> <observation>
    p_verif = subparsers.add_parser("verify", help="Record follow-up empirical verification observation")
    p_verif.add_argument("id", help="Explanation ID")
    p_verif.add_argument("observation", help="Empirical observation text (e.g. 'Confirmed zero packet drops')")

    # 8. snapshot <id>
    p_snap = subparsers.add_parser("snapshot", help="Inspect immutable point-in-time explanation snapshot")
    p_snap.add_argument("id", help="Explanation ID")

    # Default fallback: positional target argument
    # If first arg is not a subcommand, treat as target
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] not in [
        "target", "timeline", "chain", "evidence", "alternatives", "gaps", "verify", "snapshot", "-h", "--help"
    ]:
        raw_args = ["target"] + raw_args

    args = parser.parse_args(raw_args)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    svc = CausalExplanationService.get_instance()

    if args.command == "target":
        req = ExplanationRequest(
            target_entity=args.entity,
            target_state_change=args.symptom,
        )
        expl = svc.generate_explanation(req)
        print(json.dumps(expl.model_dump(mode="json"), indent=2))

    elif args.command == "timeline":
        expl = svc.get_explanation(args.id)
        if not expl:
            print(f"Error: Explanation '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(expl.event_chain.model_dump(mode="json") if expl.event_chain else {}, indent=2))

    elif args.command == "chain":
        expl = svc.get_explanation(args.id)
        if not expl:
            print(f"Error: Explanation '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([link.model_dump(mode="json") for link in expl.causal_links], indent=2))

    elif args.command == "evidence":
        expl = svc.get_explanation(args.id)
        if not expl:
            print(f"Error: Explanation '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        evidence = []
        for link in expl.causal_links:
            evidence.extend([ev.model_dump(mode="json") for ev in link.supporting_evidence])
            evidence.extend([ev.model_dump(mode="json") for ev in link.contradicting_evidence])
        print(json.dumps(evidence, indent=2))

    elif args.command == "alternatives":
        expl = svc.get_explanation(args.id)
        if not expl:
            print(f"Error: Explanation '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([alt.model_dump(mode="json") for alt in expl.alternatives], indent=2))

    elif args.command == "gaps":
        expl = svc.get_explanation(args.id)
        if not expl:
            print(f"Error: Explanation '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([g.model_dump(mode="json") for g in expl.unresolved_gaps], indent=2))

    elif args.command == "verify":
        try:
            updated = svc.verify_explanation(
                explanation_id=args.id,
                actual_observation=args.observation,
            )
            print(json.dumps(updated.model_dump(mode="json"), indent=2))
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "snapshot":
        expl = svc.get_explanation(args.id)
        if not expl:
            print(f"Error: Explanation '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps({
            "snapshot_id": f"snap_{expl.explanation_id}_v{expl.version}",
            "captured_at": expl.updated_at.isoformat(),
            "explanation": expl.model_dump(mode="json"),
        }, indent=2))


if __name__ == "__main__":
    main()
