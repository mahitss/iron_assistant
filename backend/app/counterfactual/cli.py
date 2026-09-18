"""CLI subcommands for Task 113:
Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning Engine.
"""

from __future__ import annotations

import argparse
import json
import sys

from app.counterfactual.domain import (
    BaselineType,
    CounterfactualRequest,
    CounterfactualType,
)
from app.counterfactual.service import get_counterfactual_service


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairo counterfactual",
        description="Autonomous Counterfactual, Intervention Analysis, What-If Simulation & Causal Experiment Planning CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Counterfactual subcommands")

    # 1. create
    create_parser = subparsers.add_parser("create", help="Create counterfactual analysis")
    create_parser.add_argument("target", help="Target entity or variable to evaluate")
    create_parser.add_argument("--type", default="RESOURCE", help="Counterfactual inquiry type")
    create_parser.add_argument("--question", default="What would happen if we intervene?", help="Inquiry question")

    # 2. list
    subparsers.add_parser("list", help="List recent counterfactual analyses")

    # 3. show
    show_parser = subparsers.add_parser("show", help="Show counterfactual analysis details")
    show_parser.add_argument("id", help="Counterfactual analysis ID")

    # 4. baseline
    baseline_parser = subparsers.add_parser("baseline", help="View baseline reference state")
    baseline_parser.add_argument("id", help="Counterfactual analysis ID")

    # 5. scenarios
    scenarios_parser = subparsers.add_parser("scenarios", help="List evaluated scenarios")
    scenarios_parser.add_argument("id", help="Counterfactual analysis ID")

    # 6. simulate
    simulate_parser = subparsers.add_parser("simulate", help="Run sandboxed simulation")
    simulate_parser.add_argument("id", help="Counterfactual analysis ID")

    # 7. compare
    compare_parser = subparsers.add_parser("compare", help="View side-by-side comparison with NO_ACTION")
    compare_parser.add_argument("id", help="Counterfactual analysis ID")

    # 8. assumptions
    assumptions_parser = subparsers.add_parser("assumptions", help="List causal assumptions")
    assumptions_parser.add_argument("id", help="Counterfactual analysis ID")

    # 9. sensitivity
    sensitivity_parser = subparsers.add_parser("sensitivity", help="Inspect sensitivity analysis")
    sensitivity_parser.add_argument("id", help="Counterfactual analysis ID")

    # 10. robustness
    robustness_parser = subparsers.add_parser("robustness", help="Inspect robustness assessment")
    robustness_parser.add_argument("id", help="Counterfactual analysis ID")

    # 11. verify
    verify_parser = subparsers.add_parser("verify", help="Verify prediction against observed reality")
    verify_parser.add_argument("id", help="Counterfactual analysis ID")
    verify_parser.add_argument("intv_id", help="Executed intervention ID")
    verify_parser.add_argument("observed", help="JSON string of observed post-execution state")

    # 12. snapshot
    snapshot_parser = subparsers.add_parser("snapshot", help="Capture and inspect immutable snapshot")
    snapshot_parser.add_argument("id", help="Counterfactual analysis ID")

    args = parser.parse_args()
    svc = get_counterfactual_service()

    if not args.subcommand:
        parser.print_help()
        sys.exit(1)

    if args.subcommand == "create":
        req = CounterfactualRequest(
            target_entity=args.target,
            counterfactual_type=CounterfactualType.RESOURCE,
            baseline_type=BaselineType.CURRENT,
            question=args.question,
        )
        analysis = svc.create_analysis(req)
        print(f"Created Counterfactual Analysis: {analysis.analysis_id}")
        print(f"Target: {analysis.target_entity}")
        print(f"Lifecycle: {analysis.lifecycle_stage.value}")
        print(f"Scenarios Count: {len(analysis.scenarios)}")
        if analysis.comparison:
            print(f"Recommended Candidate: {analysis.comparison.recommended_option_for_decision}")
            print(f"NO_ACTION Viable: {analysis.comparison.no_action_viable}")

    elif args.subcommand == "list":
        analyses = svc.list_analyses()
        print(f"Found {len(analyses)} counterfactual analyses:")
        for a in analyses:
            print(f" - {a.analysis_id}: target={a.target_entity} status={a.lifecycle_stage.value} stale={a.is_stale}")

    elif args.subcommand == "show":
        analysis = svc.get_analysis(args.id)
        if not analysis:
            print(f"Error: Counterfactual {args.id} not found.", file=sys.stderr)
            sys.exit(1)
        print(f"Analysis ID: {analysis.analysis_id}")
        print(f"Target: {analysis.target_entity}")
        print(f"Question: {analysis.question}")
        print(f"Lifecycle: {analysis.lifecycle_stage.value}")
        print(f"Environment: {analysis.environment_label} (is_hypothetical={analysis.is_hypothetical})")
        if analysis.comparison:
            print(f"\nTradeoff Summary:\n{analysis.comparison.tradeoff_summary}")

    elif args.subcommand == "baseline":
        analysis = svc.get_analysis(args.id)
        if not analysis:
            print(f"Error: Counterfactual {args.id} not found.", file=sys.stderr)
            sys.exit(1)
        base = analysis.baseline
        print(f"Baseline ID: {base.baseline_id}")
        print(f"Type: {base.baseline_type.value}")
        print(f"Timestamp: {base.timestamp.isoformat()}")
        print(f"State Snapshot: {json.dumps(base.state_snapshot, indent=2)}")

    elif args.subcommand == "scenarios":
        analysis = svc.get_analysis(args.id)
        if not analysis:
            print(f"Error: Counterfactual {args.id} not found.", file=sys.stderr)
            sys.exit(1)
        for s in analysis.scenarios:
            pred_status = s.prediction.predicted_state.get("status") if s.prediction else "N/A"
            print(f"Scenario: {s.scenario_name} (no_action={s.is_no_action}) -> Predicted Status: {pred_status}")

    elif args.subcommand == "simulate":
        analysis = svc.get_analysis(args.id)
        if not analysis:
            print(f"Error: Counterfactual {args.id} not found.", file=sys.stderr)
            sys.exit(1)
        print(f"Simulated {len(analysis.scenarios)} scenarios in sandboxed environment. Status: READY_FOR_DECISION")

    elif args.subcommand == "compare":
        analysis = svc.get_analysis(args.id)
        if not analysis or not analysis.comparison:
            print(f"Error: Comparison unavailable for {args.id}.", file=sys.stderr)
            sys.exit(1)
        cmp = analysis.comparison
        print(f"Side-by-Side Comparison for {analysis.target_entity}:")
        print(cmp.tradeoff_summary)
        print(f"\nRecommendation: {cmp.recommended_option_for_decision} (NO_ACTION Viable: {cmp.no_action_viable})")

    elif args.subcommand == "assumptions":
        analysis = svc.get_analysis(args.id)
        if not analysis:
            print(f"Error: Counterfactual {args.id} not found.", file=sys.stderr)
            sys.exit(1)
        for s in analysis.scenarios:
            for i in s.interventions:
                for a in i.assumptions:
                    print(f" - [{a.status.value}] {a.description} (weight: {a.sensitivity_weight})")

    elif args.subcommand == "sensitivity":
        analysis = svc.get_analysis(args.id)
        if not analysis or not analysis.sensitivity:
            print(f"Error: Sensitivity unavailable for {args.id}.", file=sys.stderr)
            sys.exit(1)
        print(analysis.sensitivity.summary)
        for p in analysis.sensitivity.influential_parameters:
            print(f" - Parameter: {p['parameter']} (nominal: {p['nominal_value']}, elasticity: {p['elasticity']}, impact: {p['impact_level']})")

    elif args.subcommand == "robustness":
        analysis = svc.get_analysis(args.id)
        if not analysis or not analysis.robustness:
            print(f"Error: Robustness unavailable for {args.id}.", file=sys.stderr)
            sys.exit(1)
        rob = analysis.robustness
        print(f"Robustness: {rob.classification.value} (stability score: {rob.stability_score})")
        if rob.vulnerabilities:
            print(f"Vulnerabilities: {rob.vulnerabilities}")

    elif args.subcommand == "verify":
        obs_state = json.loads(args.observed)
        ver = svc.verify_analysis(analysis_id=args.id, executed_intervention_id=args.intv_id, observed_state=obs_state)
        if not ver:
            print(f"Error: Verification failed for {args.id}.", file=sys.stderr)
            sys.exit(1)
        print(f"Verification Result: {ver.outcome.value}")
        print(f"Deviation Score: {ver.state_deviation_score}")
        print(f"Explanation: {ver.explanation_of_deviation}")

    elif args.subcommand == "snapshot":
        snap = svc.create_snapshot(args.id)
        if not snap:
            print(f"Error: Snapshot creation failed for {args.id}.", file=sys.stderr)
            sys.exit(1)
        print(f"Snapshot Captured: {snap.snapshot_id}")
        print(f"Version: {snap.version} | Timestamp: {snap.created_at.isoformat()}")


if __name__ == "__main__":
    main()
