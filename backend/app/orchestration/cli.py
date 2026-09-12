"""Command-line interface for Autonomous Resource Economy, Capability Allocation & Cognitive Budget Engine (Task 77).

Commands:
- resource economy
- resource demand <task_id>
- resource preempt <task_id>
- resource resume <task_id>
- resource deadlock
- resource fairness
- budget status
- budget reset <scope> <scope_id>
- budget check
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.orchestration.coordinator import default_economy_coordinator
from app.orchestration.economy_schemas import BudgetScope, PreemptionPolicy


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for kairo resource economy and cognitive budget commands."""
    parser = argparse.ArgumentParser(
        prog="kairo-economy",
        description="Kairo Autonomous Resource Economy, Capability Allocation & Cognitive Budget CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # --- Resource Subcommand Group ---
    res_p = subparsers.add_parser("resource", help="Resource economy, preemption, and contention commands")
    res_sub = res_p.add_subparsers(dest="res_command", required=True)

    # resource economy
    res_sub.add_parser("economy", help="View current resource economy health and saturation")

    # resource demand <task_id>
    dem_p = res_sub.add_parser("demand", help="Estimate resource demand for a task")
    dem_p.add_argument("task_id", help="Target task ID")
    dem_p.add_argument("--resource-id", default="res_compute_default", help="Resource ID")
    dem_p.add_argument("--tokens", type=int, default=1000, help="Estimated tokens")
    dem_p.add_argument("--calls", type=int, default=1, help="Model calls")
    dem_p.add_argument("--priority", type=int, default=1, help="Task priority")

    # resource preempt <task_id>
    preempt_p = res_sub.add_parser("preempt", help="Request preemption of a task")
    preempt_p.add_argument("task_id", help="Target victim task ID")
    preempt_p.add_argument("--by", required=True, dest="preempted_by", help="Preempting task ID")
    preempt_p.add_argument("--priority", type=int, default=2, help="Requestor priority")
    preempt_p.add_argument("--policy", default="COOPERATIVE", choices=["COOPERATIVE", "IMMEDIATE", "ON_SATURATION"])

    # resource resume <task_id>
    resume_p = res_sub.add_parser("resume", help="Resume a preempted task from checkpoint")
    resume_p.add_argument("task_id", help="Target task ID to resume")

    # resource deadlock
    res_sub.add_parser("deadlock", help="Detect and resolve wait-for graph deadlocks")

    # resource fairness
    res_sub.add_parser("fairness", help="View fair-share Gini coefficient and anti-starvation metrics")

    # --- Budget Subcommand Group ---
    bg_p = subparsers.add_parser("budget", help="Cognitive budget inspection and control")
    bg_sub = bg_p.add_subparsers(dest="bg_command", required=True)

    # budget status
    status_p = bg_sub.add_parser("status", help="View status of all budgets or specific scope")
    status_p.add_argument("--scope", default=None, choices=[s.value for s in BudgetScope])
    status_p.add_argument("--scope-id", default=None, help="Scope identifier")

    # budget reset <scope> <scope_id>
    reset_p = bg_sub.add_parser("reset", help="Reset a cognitive budget")
    reset_p.add_argument("scope", choices=[s.value for s in BudgetScope])
    reset_p.add_argument("scope_id", help="Scope identifier")

    # budget check
    check_p = bg_sub.add_parser("check", help="Check if demands fit in budget")
    check_p.add_argument("--tokens", type=float, default=2000.0, help="Requested tokens")
    check_p.add_argument("--calls", type=float, default=1.0, help="Requested model calls")
    check_p.add_argument("--scope", default="GLOBAL", choices=[s.value for s in BudgetScope])
    check_p.add_argument("--scope-id", default="global", help="Scope ID")

    return parser


def handle_resource_command(args: argparse.Namespace) -> int:
    """Handle resource subcommands."""
    coordinator = default_economy_coordinator

    if args.res_command == "economy":
        summary = coordinator.get_economy_overview()
        print(json.dumps(summary.model_dump(mode="json"), indent=2))
        return 0

    if args.res_command == "demand":
        demand = coordinator.economy.estimate_demand(
            task_id=args.task_id,
            resource_id=args.resource_id,
            estimated_tokens=args.tokens,
            model_calls=args.calls,
            priority=args.priority,
        )
        print(json.dumps(demand.model_dump(mode="json"), indent=2))
        return 0

    if args.res_command == "preempt":
        policy = PreemptionPolicy(args.policy)
        success, reason, rec = coordinator.request_safe_preemption(
            task_id=args.task_id,
            preempted_by_task_id=args.preempted_by,
            requestor_priority=args.priority,
            policy=policy,
        )
        if not success:
            print(f"Preemption failed: {reason}", file=sys.stderr)
            return 1
        print(json.dumps(rec.model_dump(mode="json") if rec else {}, indent=2))
        return 0

    if args.res_command == "resume":
        success, msg, snapshot = coordinator.preemption.resume_task(args.task_id)
        if not success:
            print(f"Resume failed: {msg}", file=sys.stderr)
            return 1
        print(json.dumps({"status": "RESUMED", "task_id": args.task_id, "snapshot": snapshot}, indent=2))
        return 0

    if args.res_command == "deadlock":
        resolutions = coordinator.check_and_resolve_deadlocks()
        print(json.dumps({"cycles_resolved": len(resolutions), "details": resolutions}, indent=2))
        return 0

    if args.res_command == "fairness":
        budgets = coordinator.budget.list_budgets()
        shares = {b.scope_id: sum(b.consumed.values()) for b in budgets}
        metrics = coordinator.fairness.compute_fairness_metrics(shares)
        print(json.dumps(metrics.model_dump(mode="json"), indent=2))
        return 0

    return 1


def handle_budget_command(args: argparse.Namespace) -> int:
    """Handle budget subcommands."""
    coordinator = default_economy_coordinator

    if args.bg_command == "status":
        if args.scope and args.scope_id:
            b = coordinator.budget.get_budget(BudgetScope(args.scope), args.scope_id)
            if not b:
                print(f"Budget for {args.scope}:{args.scope_id} not found", file=sys.stderr)
                return 1
            print(json.dumps(b.model_dump(mode="json"), indent=2))
        else:
            budgets = coordinator.budget.list_budgets()
            print(json.dumps([b.model_dump(mode="json") for b in budgets], indent=2))
        return 0

    if args.bg_command == "reset":
        success = coordinator.budget.reset_budget(BudgetScope(args.scope), args.scope_id)
        if not success:
            print(f"Budget reset failed: {args.scope}:{args.scope_id} not found", file=sys.stderr)
            return 1
        print(json.dumps({"status": "RESET", "scope": args.scope, "scope_id": args.scope_id}, indent=2))
        return 0

    if args.bg_command == "check":
        demands = {"CONTEXT_TOKENS": args.tokens, "MODEL_CALLS": args.calls}
        scopes = [(BudgetScope(args.scope), args.scope_id)]
        allowed, reason, near = coordinator.budget.check_budget(demands, scopes)
        print(json.dumps({"allowed": allowed, "reason": reason, "near_limits": near}, indent=2))
        return 0 if allowed else 1

    return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.subcommand == "resource":
        return handle_resource_command(args)
    elif args.subcommand == "budget":
        return handle_budget_command(args)

    return 1


if __name__ == "__main__":
    sys.exit(main())
