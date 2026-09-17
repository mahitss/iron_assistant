"""Command-line interface for Task 105:
Autonomous Adaptation, Experiment Orchestration & Governed Evolution Engine.
Implements 'kairo adapt' and 'kairo evolve' commands.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from typing import Any, Optional

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.adaptation.domain import (
    EvolutionProposalStatus,
    ProgramStatus,
    ReviewStatus,
    RunStatus,
)
from app.adaptation.service import AutonomousAdaptationService, get_adaptation_service


def build_adapt_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo adapt' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("adapt", help="Autonomous adaptation & experiment commands")
    else:
        parser = argparse.ArgumentParser(prog="kairo adapt", description="Kairo Adaptation CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. programs
    prog_p = sub.add_parser("programs", help="List or create adaptation programs")
    prog_p.add_argument("--status", choices=[s.value for s in ProgramStatus], help="Filter by program status")
    prog_p.add_argument("--create", action="store_true", help="Create an adaptation program interactively/with flags")
    prog_p.add_argument("--title", help="Program title")
    prog_p.add_argument("--capability", help="Affected capability name")

    # 2. hypotheses
    hyp_p = sub.add_parser("hypotheses", help="List or formulate adaptation hypotheses")
    hyp_p.add_argument("--program", help="Filter by program ID")

    # 3. experiments
    exp_p = sub.add_parser("experiments", help="List experiment runs")
    exp_p.add_argument("--status", choices=[s.value for s in RunStatus], help="Filter by run status")

    # 4. experiment show
    show_p = sub.add_parser("experiment", help="Inspect or control a specific experiment")
    show_sub = show_p.add_subparsers(dest="action", required=True)

    s_show = show_sub.add_parser("show", help="Show experiment details")
    s_show.add_argument("run_id", help="Experiment run ID")

    s_start = show_sub.add_parser("start", help="Start an experiment run")
    s_start.add_argument("plan_id", help="Experiment plan ID to launch")
    s_start.add_argument("--samples", type=int, default=20, help="Target sample count")

    s_stop = show_sub.add_parser("stop", help="Stop an active experiment run")
    s_stop.add_argument("run_id", help="Experiment run ID")
    s_stop.add_argument("--reason", default="Manual stop via CLI", help="Stop reason")

    s_pause = show_sub.add_parser("pause", help="Pause an active experiment run")
    s_pause.add_argument("run_id", help="Experiment run ID")

    s_resume = show_sub.add_parser("resume", help="Resume a paused experiment run")
    s_resume.add_argument("run_id", help="Experiment run ID")

    # 5. compare
    cmp_p = sub.add_parser("compare", help="Inspect statistical comparisons across variants")
    cmp_p.add_argument("--run-id", help="Filter by run ID")

    # 6. evidence
    evi_p = sub.add_parser("evidence", help="Inspect sealed immutable evidence package")
    evi_p.add_argument("run_id", help="Experiment run ID")

    # 7. gates
    gate_p = sub.add_parser("gates", help="Inspect evaluated safety and security gates")
    gate_p.add_argument("--run-id", help="Filter by run ID")

    return parser


def build_evolve_parser(subparsers: Optional[argparse._SubParsersAction] = None) -> argparse.ArgumentParser:
    """Builds argument parser for 'kairo evolve' subcommands."""
    if subparsers:
        parser = subparsers.add_parser("evolve", help="Governed evolution & capability change commands")
    else:
        parser = argparse.ArgumentParser(prog="kairo evolve", description="Kairo Governed Evolution CLI")

    sub = parser.add_subparsers(dest="subcommand", required=True)

    # 1. proposals
    prop_p = sub.add_parser("proposals", help="List evolution proposals")
    prop_p.add_argument("--status", choices=[s.value for s in EvolutionProposalStatus], help="Filter by proposal status")

    # 2. proposal show
    p_show = sub.add_parser("proposal", help="Inspect an evolution proposal")
    p_sub = p_show.add_subparsers(dest="action", required=True)
    p_inspect = p_sub.add_parser("show", help="Show proposal details")
    p_inspect.add_argument("proposal_id", help="Evolution proposal ID")

    # 3. reviews
    rev_p = sub.add_parser("reviews", help="List formal reviews on evolution proposals")
    rev_p.add_argument("--proposal-id", help="Filter by proposal ID")

    # 4. changesets
    cs_p = sub.add_parser("changesets", help="List immutable changesets")
    cs_p.add_argument("--proposal-id", help="Filter by proposal ID")

    # 5. validate
    val_p = sub.add_parser("validate", help="Execute multi-suite pre-rollout validation")
    val_p.add_argument("proposal_id", help="Evolution proposal ID")
    val_p.add_argument("changeset_id", help="Evolution changeset ID")

    # 6. history
    sub.add_parser("history", help="Show complete auditable adaptation and evolution timeline")

    return parser


def build_parser() -> argparse.ArgumentParser:
    """Top-level unified parser supporting both 'adapt' and 'evolve'."""
    parser = argparse.ArgumentParser(prog="kairo", description="Kairo Autonomous Adaptation & Governed Evolution")
    sub = parser.add_subparsers(dest="module", required=True)
    build_adapt_parser(sub)
    build_evolve_parser(sub)
    return parser


def handle_adapt_command(args: argparse.Namespace, service: AutonomousAdaptationService) -> int:
    """Dispatches 'kairo adapt' subcommands."""
    sub = args.subcommand

    if sub == "programs":
        progs = service.list_programs(status=ProgramStatus(args.status) if args.status else None)
        print(f"\nRegistered Adaptation Programs ({len(progs)}):")
        print("-" * 80)
        for p in progs:
            print(f"[{p.status.value:<12}] {p.id} | {p.affected_capability:<20} | {p.title}")
        return 0

    elif sub == "hypotheses":
        hyps = list(service.hypothesis_engine.hypotheses.values())
        print(f"\nFormulated Hypotheses ({len(hyps)}):")
        print("-" * 80)
        for h in hyps:
            print(f"{h.id} (conf={h.confidence:.2f}): IF {h.condition_change[:35]}... THEN {h.expected_outcome[:35]}...")
        return 0

    elif sub == "experiments":
        runs = list(service.experiment_engine.runs.values())
        if args.status:
            runs = [r for r in runs if r.status == RunStatus(args.status)]
        print(f"\nExperiment Runs ({len(runs)}):")
        print("-" * 80)
        for r in runs:
            print(f"[{r.status.value:<12}] {r.id} | Plan: {r.plan_id} | Stage {r.stage_number} | Env: {r.environment.value}")
        return 0

    elif sub == "experiment":
        act = args.action
        if act == "show":
            run = service.experiment_engine.runs.get(args.run_id)
            if not run:
                print(f"Error: Run '{args.run_id}' not found.")
                return 1
            print(json.dumps({
                "id": run.id,
                "plan_id": run.plan_id,
                "program_id": run.program_id,
                "stage_number": run.stage_number,
                "environment": run.environment.value,
                "status": run.status.value,
                "current_samples": run.current_sample_count,
                "target_samples": run.target_sample_count,
                "stop_reason": run.stop_reason,
            }, indent=2))
            return 0
        elif act == "start":
            run = service.start_experiment(plan_id=args.plan_id, target_sample_count=args.samples)
            print(f"Launched Experiment Run: {run.id} (status={run.status.value})")
            return 0
        elif act == "stop":
            run = service.experiment_engine.stop_run(run_id=args.run_id, reason=args.reason)
            print(f"Stopped Experiment Run: {run.id} (status={run.status.value})")
            return 0
        elif act == "pause":
            run = service.experiment_engine.runs.get(args.run_id)
            if run:
                run.transition_to(RunStatus.PAUSED, reason="CLI pause")
                print(f"Paused Experiment Run: {run.id}")
            return 0
        elif act == "resume":
            run = service.experiment_engine.runs.get(args.run_id)
            if run:
                run.transition_to(RunStatus.RUNNING, reason="CLI resume")
                print(f"Resumed Experiment Run: {run.id}")
            return 0

    elif sub == "compare":
        cmps = list(service.comparison_engine.comparisons.values())
        if args.run_id:
            cmps = [c for c in cmps if c.run_id == args.run_id]
        print(f"\nExperiment Comparisons ({len(cmps)}):")
        print("-" * 80)
        for c in cmps:
            print(f"[{c.verdict.value:<12}] Run: {c.run_id} | Samples: {c.sample_size:<4} | {c.rationale}")
        return 0

    elif sub == "evidence":
        evi = next((e for e in service.comparison_engine.evidences.values() if e.run_id == args.run_id), None)
        if not evi:
            print(f"Error: No sealed evidence found for run '{args.run_id}'.")
            return 1
        print(json.dumps({
            "id": evi.id,
            "run_id": evi.run_id,
            "program_id": evi.program_id,
            "hypothesis": evi.hypothesis_text,
            "safety_passed": evi.safety_gates_passed,
            "immutable_hash": evi.immutable_hash,
            "created_at": evi.created_at.isoformat(),
        }, indent=2))
        return 0

    elif sub == "gates":
        gates: list[Any] = []
        if args.run_id:
            gates = service.experiment_engine.gates.get(args.run_id, [])
        else:
            for glist in service.experiment_engine.gates.values():
                gates.extend(glist)
        print(f"\nEvaluated Gates ({len(gates)}):")
        print("-" * 80)
        for g in gates:
            st = "PASS" if g.passed else "FAIL"
            print(f"[{st:<4}] {g.gate_name:<30} | Run: {g.run_id} | {g.reason}")
        return 0

    return 0


def handle_evolve_command(args: argparse.Namespace, service: AutonomousAdaptationService) -> int:
    """Dispatches 'kairo evolve' subcommands."""
    sub = args.subcommand

    if sub == "proposals":
        props = list(service.evolution_engine.proposals.values())
        if args.status:
            props = [p for p in props if p.status == EvolutionProposalStatus(args.status)]
        print(f"\nEvolution Proposals ({len(props)}):")
        print("-" * 80)
        for p in props:
            print(f"[{p.status.value:<14}] {p.id} | {p.affected_capability} ({p.current_version} -> {p.target_version}) | {p.title}")
        return 0

    elif sub == "proposal":
        act = args.action
        if act == "show":
            p = service.evolution_engine.proposals.get(args.proposal_id)
            if not p:
                print(f"Error: Proposal '{args.proposal_id}' not found.")
                return 1
            print(json.dumps({
                "id": p.id,
                "title": p.title,
                "affected_capability": p.affected_capability,
                "version_transition": f"{p.current_version} -> {p.target_version}",
                "evidence_id": p.evidence_id,
                "status": p.status.value,
                "confidence": p.confidence,
                "rollback_plan": p.rollback_plan,
            }, indent=2))
            return 0

    elif sub == "reviews":
        revs = list(service.evolution_engine.reviews.values())
        if args.proposal_id:
            revs = [r for r in revs if r.proposal_id == args.proposal_id]
        print(f"\nEvolution Reviews ({len(revs)}):")
        print("-" * 80)
        for r in revs:
            print(f"[{r.status.value:<8}] Proposal: {r.proposal_id} | Reviewer: {r.reviewer} | {r.rationale}")
        return 0

    elif sub == "changesets":
        css = list(service.evolution_engine.changesets.values())
        if args.proposal_id:
            css = [c for c in css if c.proposal_id == args.proposal_id]
        print(f"\nEvolution ChangeSets ({len(css)}):")
        print("-" * 80)
        for c in css:
            print(f"{c.id} | Proposal: {c.proposal_id} | {c.capability_id} ({c.current_version} -> {c.candidate_version}) | Hash: {c.content_hash[:12]}...")
        return 0

    elif sub == "validate":
        val = service.validate_evolution(proposal_id=args.proposal_id, changeset_id=args.changeset_id)
        print(f"Validation Result: {val.overall_status.value} (Holdout passed: {val.holdout_passed})")
        return 0

    elif sub == "history":
        print(f"\nAdaptation Audit Timeline ({len(service.events)} events):")
        print("-" * 80)
        for e in service.events:
            print(f"{e.occurred_at.strftime('%Y-%m-%d %H:%M:%S')} | [{e.event_type:<24}] {e.payload}")
        return 0

    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """CLI main entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    service = get_adaptation_service()

    if args.module == "adapt":
        return handle_adapt_command(args, service)
    elif args.module == "evolve":
        return handle_evolve_command(args, service)
    return 0


if __name__ == "__main__":
    sys.exit(main())
