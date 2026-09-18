"""CLI subcommands for Task 114:
Autonomous Active Observation, Value-of-Information, Information Acquisition & Uncertainty Reduction Engine.
"""

from __future__ import annotations

import argparse
import json
import sys

from app.observation.domain import ObservationScope
from app.observation.schemas import ObservationPlanCreateRequest
from app.observation.service import get_observation_service


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairo observe",
        description="Autonomous Active Observation, Value-of-Information & Uncertainty Reduction CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Observation subcommands")

    # 1. gaps
    gaps_parser = subparsers.add_parser("gaps", help="List identified information gaps")
    gaps_parser.add_argument("--plan-id", default=None, help="Filter by observation plan ID")

    # 2. plan
    plan_parser = subparsers.add_parser("plan", help="Create new observation plan")
    plan_parser.add_argument("target", help="Target entity to observe")
    plan_parser.add_argument("--question", default="What don't I know and what observation is needed?", help="Inquiry question")
    plan_parser.add_argument("--budget", type=float, default=10.0, help="Budget units")

    # 3. candidates
    cand_parser = subparsers.add_parser("candidates", help="List observation candidates for plan")
    cand_parser.add_argument("id", help="Observation plan ID")

    # 4. value
    val_parser = subparsers.add_parser("value", help="Inspect candidate Value-of-Information (VoI)")
    val_parser.add_argument("id", help="Observation plan ID")

    # 5. cost
    cost_parser = subparsers.add_parser("cost", help="Inspect observation costs")
    cost_parser.add_argument("id", help="Observation plan ID")

    # 6. risk
    risk_parser = subparsers.add_parser("risk", help="Inspect observation risks")
    risk_parser.add_argument("id", help="Observation plan ID")

    # 7. run
    run_parser = subparsers.add_parser("run", help="Execute observation candidate")
    run_parser.add_argument("id", help="Observation plan ID")
    run_parser.add_argument("--candidate-id", default=None, help="Optional specific candidate ID")

    # 8. show
    show_parser = subparsers.add_parser("show", help="Show full observation plan details")
    show_parser.add_argument("id", help="Observation plan ID")

    # 9. verify
    veri_parser = subparsers.add_parser("verify", help="Inspect observation verifications")
    veri_parser.add_argument("id", help="Observation plan ID")

    # 10. uncertainty
    unc_parser = subparsers.add_parser("uncertainty", help="Inspect epistemic uncertainty")
    unc_parser.add_argument("--target", default="system_core", help="Target entity")

    # 11. history
    subparsers.add_parser("history", help="List historical observation plans")

    args = parser.parse_args()
    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    svc = get_observation_service()

    if args.subcommand == "gaps":
        gaps = svc.get_gaps(args.plan_id)
        print(json.dumps([g.model_dump(mode="json") for g in gaps], indent=2))

    elif args.subcommand == "plan":
        req = ObservationPlanCreateRequest(
            target_entity=args.target,
            question=args.question,
            budget_units=args.budget,
        )
        plan = svc.create_observation_plan(req)
        print(f"Observation plan created: {plan.plan_id}")
        print(json.dumps(plan.model_dump(mode="json"), indent=2))

    elif args.subcommand == "candidates":
        plan = svc.get_plan(args.id)
        if not plan:
            print(f"Error: Plan '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([c.model_dump(mode="json") for c in plan.candidates], indent=2))

    elif args.subcommand == "value":
        plan = svc.get_plan(args.id)
        if not plan:
            print(f"Error: Plan '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        values = [
            {
                "candidate_id": c.candidate_id,
                "name": c.name,
                "method": c.method.value,
                "value_estimate": c.value_estimate.model_dump(mode="json") if c.value_estimate else None,
            }
            for c in plan.candidates
        ]
        print(json.dumps(values, indent=2))

    elif args.subcommand == "cost":
        plan = svc.get_plan(args.id)
        if not plan:
            print(f"Error: Plan '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        costs = [
            {"candidate_id": c.candidate_id, "name": c.name, "cost": c.cost.model_dump(mode="json")}
            for c in plan.candidates
        ]
        print(json.dumps({"budget": plan.budget.model_dump(mode="json"), "candidates": costs}, indent=2))

    elif args.subcommand == "risk":
        plan = svc.get_plan(args.id)
        if not plan:
            print(f"Error: Plan '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        risks = [
            {"candidate_id": c.candidate_id, "name": c.name, "risk": c.risk.model_dump(mode="json")}
            for c in plan.candidates
        ]
        print(json.dumps(risks, indent=2))

    elif args.subcommand == "run":
        try:
            plan = svc.execute_observation(args.id)
            print(f"Executed observation plan '{args.id}'. Status: {plan.status.value}, Stance: {plan.recommended_stance}")
            print(json.dumps(plan.model_dump(mode="json"), indent=2))
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.subcommand == "show":
        plan = svc.get_plan(args.id)
        if not plan:
            print(f"Error: Plan '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(plan.model_dump(mode="json"), indent=2))

    elif args.subcommand == "verify":
        plan = svc.get_plan(args.id)
        if not plan:
            print(f"Error: Plan '{args.id}' not found.", file=sys.stderr)
            sys.exit(1)
        veris = [v.model_dump(mode="json") for v in plan.verifications.values()]
        print(json.dumps(veris, indent=2))

    elif args.subcommand == "uncertainty":
        unc = svc.get_uncertainty(args.target)
        print(json.dumps(unc.model_dump(mode="json"), indent=2))

    elif args.subcommand == "history":
        plans = svc.list_plans()
        print(json.dumps([p.model_dump(mode="json") for p in plans], indent=2))


if __name__ == "__main__":
    main()
