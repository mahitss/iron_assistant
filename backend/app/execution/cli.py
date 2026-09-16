"""CLI tool for Task 95: Action Transactions and Execution Governance (kairo-action)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.execution.domain import TargetBinding, TargetType
from app.execution.service import get_execution_governance_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kairo-action",
        description="KAIRO Action Transaction & Execution Governance Engine CLI (Task 95)",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    p_list = subparsers.add_parser("list", help="List recent action transactions")
    p_list.add_argument("--limit", type=int, default=20, help="Maximum transactions to list")

    # 2. inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect transaction details")
    p_inspect.add_argument("transaction_id", type=str, help="Transaction ID")

    # 3. preflight
    p_preflight = subparsers.add_parser("preflight", help="Execute 18-gate preflight validation")
    p_preflight.add_argument("transaction_id", type=str, help="Transaction ID")

    # 4. execute
    p_execute = subparsers.add_parser("execute", help="Execute action through ToolExecutor")
    p_execute.add_argument("transaction_id", type=str, help="Transaction ID")
    p_execute.add_argument("--approval-id", type=str, default=None, help="Approval ID if required")

    # 5. cancel
    p_cancel = subparsers.add_parser("cancel", help="Cancel transaction")
    p_cancel.add_argument("transaction_id", type=str, help="Transaction ID")
    p_cancel.add_argument("--reason", type=str, default="User cancelled", help="Cancellation reason")

    # 6. verify
    p_verify = subparsers.add_parser("verify", help="Inspect verification state and postconditions")
    p_verify.add_argument("transaction_id", type=str, help="Transaction ID")

    # 7. rollback
    p_rollback = subparsers.add_parser("rollback", help="Initiate rollback compensation")
    p_rollback.add_argument("transaction_id", type=str, help="Transaction ID")
    p_rollback.add_argument("--reason", type=str, default="Operator rollback", help="Rollback reason")

    # 8. reconcile
    p_reconcile = subparsers.add_parser("reconcile", help="Reconcile an UNKNOWN state transaction")
    p_reconcile.add_argument("transaction_id", type=str, help="Transaction ID")

    # 9. outcome
    p_outcome = subparsers.add_parser("outcome", help="View verified transaction outcome")
    p_outcome.add_argument("transaction_id", type=str, help="Transaction ID")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = get_execution_governance_service()

    if args.subcommand == "list":
        txns = service.list_transactions(limit=args.limit)
        print(f"--- Action Transactions ({len(txns)}) ---")
        for t in txns:
            print(f"[{t.status.value:14}] {t.transaction_id} | Cap: {t.capability_id} | Target: {t.target.target_id}")
        return 0

    elif args.subcommand == "inspect":
        txn = service.get_transaction(args.transaction_id)
        if not txn:
            print(f"Transaction '{args.transaction_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps(txn.model_dump(mode="json"), indent=2))
        return 0

    elif args.subcommand == "preflight":
        passed, txn = asyncio.run(service.run_preflight(args.transaction_id))
        print(f"Preflight Result: {'PASSED' if passed else 'FAILED'} (Status: {txn.status.value})")
        for gate in txn.preflight_checks:
            mark = "✓" if gate.passed else "✗"
            print(f"  {mark} {gate.gate_name}: {gate.reason} ({gate.latency_ms}ms)")
        return 0 if passed else 1

    elif args.subcommand == "execute":
        txn = asyncio.run(service.execute_transaction(args.transaction_id, approval_id=args.approval_id))
        print(f"Execution completed. Transaction status: {txn.status.value} (Outcome: {txn.outcome_type})")
        return 0 if txn.status.value == "SUCCEEDED" else 1

    elif args.subcommand == "cancel":
        txn = asyncio.run(service.cancel_transaction(args.transaction_id, reason=args.reason))
        print(f"Transaction '{txn.transaction_id}' status is now: {txn.status.value}")
        return 0

    elif args.subcommand == "rollback":
        txn = asyncio.run(service.rollback_transaction(args.transaction_id, reason=args.reason))
        print(f"Rollback completed. Transaction status: {txn.status.value}")
        return 0

    elif args.subcommand == "reconcile":
        txn = asyncio.run(service.reconcile_transaction(args.transaction_id))
        print(f"Reconciliation completed. Transaction status: {txn.status.value}")
        return 0

    elif args.subcommand == "outcome":
        txn = service.get_transaction(args.transaction_id)
        if not txn:
            print(f"Transaction '{args.transaction_id}' not found.", file=sys.stderr)
            return 1
        print(json.dumps({
            "transaction_id": txn.transaction_id,
            "status": txn.status.value,
            "outcome_type": txn.outcome_type.value if txn.outcome_type else None,
            "outcome_summary": txn.outcome_summary,
            "deviation_score": txn.deviation_score,
            "regret_score": txn.regret_score,
        }, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
