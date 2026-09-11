"""Command-line interface for Autonomous Resilience & Recovery Engine (Task 76).

Commands:
- resilience assess
- resilience inspect
- resilience gaps
- resilience simulate
- resilience bottlenecks
- recovery list
- recovery inspect
- recovery plan
- recovery verify
- recovery history
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.resilience.intelligence import get_resilience_intelligence_coordinator


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for kairo resilience & recovery commands."""
    parser = argparse.ArgumentParser(
        prog="kairo-resilience",
        description="Kairo Autonomous Resilience, Recovery, Containment & Adaptive Defense CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # --- Resilience Group ---
    res_p = subparsers.add_parser("resilience", help="Resilience assessment and gap commands")
    res_sub = res_p.add_subparsers(dest="res_command", required=True)

    # resilience assess
    assess_p = res_sub.add_parser("assess", help="Run resilience assessment")
    assess_p.add_argument("--target", default="CORE", help="Target component or cluster")
    assess_p.add_argument("--scope", default="SYSTEM", help="Scope of assessment")

    # resilience inspect
    inspect_p = res_sub.add_parser("inspect", help="Inspect a resilience assessment by ID")
    inspect_p.add_argument("assessment_id", help="Assessment ID")

    # resilience gaps
    gaps_p = res_sub.add_parser("gaps", help="List detected resilience gaps")
    gaps_p.add_argument("assessment_id", help="Assessment ID")

    # resilience simulate
    sim_p = res_sub.add_parser("simulate", help="Simulate failure scenarios for assessment")
    sim_p.add_argument("assessment_id", help="Assessment ID")

    # resilience bottlenecks
    res_sub.add_parser("bottlenecks", help="Show systemic bottlenecks and SPoFs")

    # --- Recovery Group ---
    rec_p = subparsers.add_parser("recovery", help="Recovery planning and verification commands")
    rec_sub = rec_p.add_subparsers(dest="rec_command", required=True)

    # recovery list
    rec_sub.add_parser("list", help="List active recovery plans")

    # recovery inspect
    rec_insp_p = rec_sub.add_parser("inspect", help="Inspect a recovery plan by ID")
    rec_insp_p.add_argument("plan_id", help="Recovery plan ID")

    # recovery plan
    rec_plan_p = rec_sub.add_parser("plan", help="Generate recovery and containment plan")
    rec_plan_p.add_argument("cascade", nargs="+", help="Cascade sequence entities (e.g. nodeA nodeB nodeC)")
    rec_plan_p.add_argument("--incident", default=None, help="Incident ID")

    # recovery verify
    rec_ver_p = rec_sub.add_parser("verify", help="Run deterministic verification on plan")
    rec_ver_p.add_argument("plan_id", help="Recovery plan ID")

    # recovery history
    rec_sub.add_parser("history", help="Show recovery history, MTTR, and post-incident lessons")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    coord = get_resilience_intelligence_coordinator()

    if args.subcommand == "resilience":
        if args.res_command == "assess":
            sample_topo = {
                "nodes": {
                    args.target: {"criticality": 0.8, "scope": args.scope, "has_redundancy": False},
                    "db_primary": {"criticality": 0.9, "has_redundancy": True, "backups": [{"mode": "active"}]},
                },
                "edges": [{"source": "db_primary", "target": args.target}],
            }
            ass = coord.assess_resilience(scope=args.scope, target=args.target, topology=sample_topo)
            print(json.dumps(ass.model_dump(mode="json"), indent=2))
            return 0

        elif args.res_command == "inspect":
            ass = coord.assess_assessments.get(args.assessment_id) if hasattr(coord, "assess_assessments") else coord.assessments.get(args.assessment_id)
            if not ass:
                print(f"Error: Assessment {args.assessment_id} not found", file=sys.stderr)
                return 1
            print(json.dumps(ass.model_dump(mode="json"), indent=2))
            return 0

        elif args.res_command == "gaps":
            ass = coord.assessments.get(args.assessment_id)
            if not ass:
                print(f"Error: Assessment {args.assessment_id} not found", file=sys.stderr)
                return 1
            print(json.dumps([g.model_dump(mode="json") for g in ass.gaps], indent=2))
            return 0

        elif args.res_command == "simulate":
            ass = coord.assessments.get(args.assessment_id)
            if not ass:
                print(f"Error: Assessment {args.assessment_id} not found", file=sys.stderr)
                return 1
            scenarios = [{"gap": g.gap_type.value, "target": g.target_entity, "severity": g.severity} for g in ass.gaps]
            print(json.dumps({"assessment_id": args.assessment_id, "simulated_scenarios": scenarios}, indent=2))
            return 0

        elif args.res_command == "bottlenecks":
            latest = list(coord.assessments.values())[-1] if coord.assessments else None
            if not latest:
                print(json.dumps({"bottlenecks": [], "spofs": []}, indent=2))
            else:
                spofs = [g.target_entity for g in latest.gaps if g.gap_type.value == "single_point_of_failure"]
                print(json.dumps({
                    "bottlenecks": [b.value for b in latest.scorecard.bottleneck_dimensions],
                    "spofs": spofs,
                }, indent=2))
            return 0

    elif args.subcommand == "recovery":
        if args.rec_command == "list":
            active = [p.model_dump(mode="json") for p in coord.recovery_plans.values()]
            print(json.dumps(active, indent=2))
            return 0

        elif args.rec_command == "inspect":
            plan = coord.recovery_plans.get(args.plan_id)
            if not plan:
                print(f"Error: Recovery plan {args.plan_id} not found", file=sys.stderr)
                return 1
            print(json.dumps(plan.model_dump(mode="json"), indent=2))
            return 0

        elif args.rec_command == "plan":
            topo = {
                "nodes": {ent: {"criticality": 0.8, "recoverable": True} for ent in args.cascade},
                "edges": [{"source": args.cascade[i], "target": args.cascade[i+1]} for i in range(len(args.cascade)-1)],
            }
            plan = coord.plan_containment_and_recovery(
                incident_id=args.incident,
                cascade_path=args.cascade,
                topology=topo,
            )
            print(json.dumps(plan.model_dump(mode="json"), indent=2))
            return 0

        elif args.rec_command == "verify":
            plan = coord.recovery_plans.get(args.plan_id)
            if not plan:
                print(f"Error: Recovery plan {args.plan_id} not found", file=sys.stderr)
                return 1
            passed, res_plan = coord.verify_recovery(args.plan_id, live_telemetry={})
            print(json.dumps({"verified": passed, "state": res_plan.state.value, "confidence": res_plan.confidence}, indent=2))
            return 0

        elif args.rec_command == "history":
            trends = coord.adaptive_defense.calculate_resilience_trends()
            print(json.dumps({
                "trends": trends.model_dump(mode="json"),
                "lessons_count": len(coord.adaptive_defense.lessons_store),
                "recommendations_count": len(coord.adaptive_defense.recommendations_store),
            }, indent=2))
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
