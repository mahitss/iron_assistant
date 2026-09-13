"""Command-line interface for Kairo Autonomous Governance, Constitutional Reasoning,
and Authority Management Engine (Task 78).

Commands:
- kairo governance review --goal <goal> --action <action> ...
- kairo governance constitution show
- kairo governance constitution set --principle <name> [--weight <w>] [--strictness <s>]
- kairo governance authority check --subject <s> --action <a>
- kairo governance authority grant --subject <s> --level <l>
- kairo governance authority list --subject <s>
- kairo governance authority revoke --subject <s>
- kairo governance human list
- kairo governance human resolve <review_id> --reviewer <r> [--approve/--deny]
- kairo governance dashboard
- kairo governance escalations
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from app.policy.governance_coordinator import default_governance_coordinator
from app.policy.governance_schemas import (
    AuthorityLevel,
    GovernanceReviewRequest,
    PrincipleName,
    PrincipleStrictness,
)


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for governance commands."""
    parser = argparse.ArgumentParser(
        prog="kairo-governance",
        description="Kairo Autonomous Governance, Constitutional Reasoning & Authority Management CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. review
    rev_p = subparsers.add_parser("review", help="Evaluate candidate action for governance compliance")
    rev_p.add_argument("--goal", required=True, help="Autonomous goal description")
    rev_p.add_argument("--action", required=True, help="Action name / tool invocation")
    rev_p.add_argument("--resource", default="", help="Target resource or entity")
    rev_p.add_argument("--caller", default="default_agent", help="Actor/agent ID")
    rev_p.add_argument(
        "--authority",
        default="LIMITED",
        choices=[a.value for a in AuthorityLevel],
        help="Caller authority level",
    )
    rev_p.add_argument("--risk", default="R1_LOW", help="Risk classification")
    rev_p.add_argument("--irreversible", action="store_true", help="Action is irreversible")
    rev_p.add_argument("--destructive", action="store_true", help="Action is destructive")
    rev_p.add_argument("--uncertainty", type=float, default=0.0, help="Uncertainty score (0.0 - 1.0)")

    # 2. constitution
    const_p = subparsers.add_parser("constitution", help="Constitutional principles and inspection")
    const_sub = const_p.add_subparsers(dest="const_command", required=True)
    const_sub.add_parser("show", help="Display all constitutional principles and strictness")
    set_p = const_sub.add_parser("set", help="Update constitutional principle parameters")
    set_p.add_argument("--principle", required=True, choices=[p.value for p in PrincipleName])
    set_p.add_argument("--weight", type=float, default=None, help="Principle weight (0.0 - 1.0)")
    set_p.add_argument("--strictness", choices=[s.value for s in PrincipleStrictness], default=None)
    set_p.add_argument("--enabled", type=lambda v: v.lower() == "true", default=None)

    # 3. authority
    auth_p = subparsers.add_parser("authority", help="Authority grants and verification")
    auth_sub = auth_p.add_subparsers(dest="auth_command", required=True)

    chk_p = auth_sub.add_parser("check", help="Check if an actor has authority for an action")
    chk_p.add_argument("--subject", required=True, help="Subject ID")
    chk_p.add_argument("--action", required=True, help="Target action")
    chk_p.add_argument("--scope", default="default", help="Scope / workspace")

    grnt_p = auth_sub.add_parser("grant", help="Issue an authority grant")
    grnt_p.add_argument("--subject", required=True, help="Subject ID")
    grnt_p.add_argument("--level", required=True, choices=[a.value for a in AuthorityLevel])
    grnt_p.add_argument("--scopes", nargs="*", default=["*"], help="Allowed scopes")
    grnt_p.add_argument("--actions", nargs="*", default=["*"], help="Allowed action patterns")
    grnt_p.add_argument("--denied", nargs="*", default=[], help="Explicitly denied action patterns")

    lst_p = auth_sub.add_parser("list", help="List active grants for a subject")
    lst_p.add_argument("--subject", required=True, help="Subject ID")

    revk_p = auth_sub.add_parser("revoke", help="Revoke all grants for a subject")
    revk_p.add_argument("--subject", required=True, help="Subject ID")

    # 4. human
    hmn_p = subparsers.add_parser("human", help="Human-in-the-loop review operations")
    hmn_sub = hmn_p.add_subparsers(dest="human_command", required=True)
    hmn_sub.add_parser("list", help="List reviews waiting for human judgment")

    res_p = hmn_sub.add_parser("resolve", help="Resolve human review judgment")
    res_p.add_argument("review_id", help="Target review ID")
    res_p.add_argument("--reviewer", required=True, help="Human reviewer ID (cannot be AI agent)")
    res_grp = res_p.add_mutually_exclusive_group(required=True)
    res_grp.add_argument("--approve", action="store_true", help="Approve action")
    res_grp.add_argument("--deny", action="store_true", help="Deny action")
    res_p.add_argument("--rationale", default="", help="Explanation of judgment")

    # 5. dashboard
    subparsers.add_parser("dashboard", help="Display consolidated governance metrics")

    # 6. escalations
    esc_p = subparsers.add_parser("escalations", help="List recent privilege escalation incidents")
    esc_p.add_argument("--limit", type=int, default=20, help="Max incidents to display")

    return parser


def handle_command(args: argparse.Namespace) -> int:
    """Execute governance command dispatcher."""
    coord = default_governance_coordinator

    if args.subcommand == "review":
        req = GovernanceReviewRequest(
            goal=args.goal,
            action=args.action,
            resource=args.resource,
            caller_id=args.caller,
            caller_authority=AuthorityLevel(args.authority),
            risk_level=args.risk,
            is_irreversible=args.irreversible,
            is_destructive=args.destructive,
            uncertainty_score=args.uncertainty,
        )
        res = asyncio.run(coord.evaluate_review(req))
        print(json.dumps(res.model_dump(mode="json"), indent=2))
        return 0

    elif args.subcommand == "constitution":
        if args.const_command == "show":
            const = coord.constitutional_engine.constitution
            print(json.dumps(const.model_dump(mode="json"), indent=2))
            return 0
        elif args.const_command == "set":
            p_name = PrincipleName(args.principle)
            ok = coord.constitutional_engine.update_principle(
                name=p_name,
                weight=args.weight,
                strictness=PrincipleStrictness(args.strictness) if args.strictness else None,
                enabled=args.enabled,
            )
            print(json.dumps({"success": ok, "principle": p_name.value}))
            return 0 if ok else 1

    elif args.subcommand == "authority":
        if args.auth_command == "check":
            allowed, reason, granted_level = coord.authority_manager.check_authority(
                subject_id=args.subject,
                action=args.action,
                scope=args.scope,
            )
            print(json.dumps({
                "subject": args.subject,
                "action": args.action,
                "allowed": allowed,
                "reason": reason,
                "granted_level": granted_level.value,
            }, indent=2))
            return 0
        elif args.auth_command == "grant":
            grant = coord.authority_manager.issue_grant(
                subject_id=args.subject,
                authority_level=AuthorityLevel(args.level),
                allowed_scopes=args.scopes,
                allowed_actions=args.actions,
                denied_actions=args.denied,
            )
            print(json.dumps(grant.model_dump(mode="json"), indent=2))
            return 0
        elif args.auth_command == "list":
            grants = coord.authority_manager.get_active_grants(args.subject)
            highest = coord.authority_manager.get_highest_authority(args.subject)
            print(json.dumps({
                "subject": args.subject,
                "highest_level": highest.value,
                "grants": [g.model_dump(mode="json") for g in grants],
            }, indent=2))
            return 0
        elif args.auth_command == "revoke":
            count = coord.authority_manager.revoke_grants(args.subject)
            print(json.dumps({"subject": args.subject, "revoked_count": count}, indent=2))
            return 0

    elif args.subcommand == "human":
        if args.human_command == "list":
            reviews = coord.list_pending_human_reviews()
            print(json.dumps([r.model_dump(mode="json") for r in reviews], indent=2))
            return 0
        elif args.human_command == "resolve":
            try:
                res = coord.resolve_human_review(
                    review_id=args.review_id,
                    reviewer_id=args.reviewer,
                    approved=args.approve,
                    rationale=args.rationale,
                )
                print(json.dumps(res.model_dump(mode="json"), indent=2))
                return 0
            except Exception as e:
                print(json.dumps({"error": str(e)}), file=sys.stderr)
                return 1

    elif args.subcommand == "dashboard":
        dash = coord.get_dashboard_summary()
        print(json.dumps(dash.model_dump(mode="json"), indent=2))
        return 0

    elif args.subcommand == "escalations":
        incidents = coord.escalation_detector.get_recent_incidents(limit=args.limit)
        print(json.dumps([i.model_dump(mode="json") for i in incidents], indent=2))
        return 0

    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(handle_command(args))


if __name__ == "__main__":
    main()
