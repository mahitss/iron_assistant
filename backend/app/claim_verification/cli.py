"""CLI subcommands for Task 116 (Section 41):
Kairo Autonomous Claim Verification, Source Integrity & Evidence Provenance Engine.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import List, Optional

from app.claim_verification.schemas import CreateVerificationRequest
from app.claim_verification.service import ClaimVerificationService


def main(args_list: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="kairo verify",
        description="Autonomous Claim Verification & Evidence Provenance Engine CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Verification subcommands")

    # 1. create <claim_text>
    create_parser = subparsers.add_parser("create", help="Initiate a verification case")
    create_parser.add_argument("claim", help="Claim statement to verify")
    create_parser.add_argument("--title", default=None, help="Optional human-readable title")
    create_parser.add_argument("--source-uri", default="cli://input", help="URI of initial source")
    create_parser.add_argument("--evidence-text", default=None, help="Optional text of supporting evidence")

    # 2. list
    list_parser = subparsers.add_parser("list", help="List verification cases")
    list_parser.add_argument("--status", default=None, help="Filter by case status")
    list_parser.add_argument("--limit", type=int, default=50, help="Max cases to return")

    # 3. show <case_id>
    show_parser = subparsers.add_parser("show", help="Show verification case details")
    show_parser.add_argument("id", help="Case ID")

    # 4. evidence <case_id>
    evi_parser = subparsers.add_parser("evidence", help="Show supporting evidence for case")
    evi_parser.add_argument("id", help="Case ID")

    # 5. provenance <case_id>
    prov_parser = subparsers.add_parser("provenance", help="Show provenance DAG for case")
    prov_parser.add_argument("id", help="Case ID")

    # 6. contradictions <case_id>
    contra_parser = subparsers.add_parser("contradictions", help="Show detected contradictions")
    contra_parser.add_argument("id", help="Case ID")

    # 7. revalidate <case_id>
    reval_parser = subparsers.add_parser("revalidate", help="Trigger revalidation of case")
    reval_parser.add_argument("id", help="Case ID")

    # 8. explain <case_id>
    expl_parser = subparsers.add_parser("explain", help="Show full verification explanation tree")
    expl_parser.add_argument("id", help="Case ID")

    # 9. source <source_id>
    src_parser = subparsers.add_parser("source", help="Show source trust profile and metadata")
    src_parser.add_argument("id", help="Source ID")

    # 10. lineage <evidence_id>
    lin_parser = subparsers.add_parser("lineage", help="Trace lineage from evidence artifact to origin")
    lin_parser.add_argument("id", help="Evidence ID")

    args = parser.parse_args(args_list)
    svc = ClaimVerificationService.get_instance()

    async def run() -> None:
        if args.subcommand == "create":
            sources = [{"uri": args.source_uri, "publisher": "cli_user"}]
            evidence = []
            if args.evidence_text:
                evidence.append({"content_text": args.evidence_text})

            req = CreateVerificationRequest(
                claim_text=args.claim,
                title=args.title,
                sources=sources,
                evidence=evidence,
            )
            case, result = await svc.create_verification(req)
            print(f"Created verification case '{case.case_id}' with status {case.status.value}")
            print(json.dumps({
                "case": case.to_dict(),
                "result": result.to_dict(),
            }, indent=2))

        elif args.subcommand == "list":
            cases = await svc.list_verifications(status=args.status, limit=args.limit)
            print(json.dumps([c.to_dict() for c in cases], indent=2))

        elif args.subcommand == "show":
            case = await svc.get_verification(args.id)
            if not case:
                print(f"Error: Verification case '{args.id}' not found.", file=sys.stderr)
                sys.exit(1)
            result = await svc.get_result_for_case(args.id)
            print(json.dumps({
                "case": case.to_dict(),
                "result": result.to_dict() if result else None,
            }, indent=2))

        elif args.subcommand == "evidence":
            evidence = await svc.get_evidence_for_case(args.id)
            print(json.dumps([e.to_dict() for e in evidence], indent=2))

        elif args.subcommand == "provenance":
            graph = await svc.get_provenance_graph(args.id)
            print(json.dumps(graph, indent=2))

        elif args.subcommand == "contradictions":
            contras = await svc.get_contradictions_for_case(args.id)
            print(json.dumps([c.to_dict() for c in contras], indent=2))

        elif args.subcommand == "revalidate":
            res = await svc.revalidate_verification(args.id)
            if not res:
                print(f"Error: Verification case '{args.id}' not found.", file=sys.stderr)
                sys.exit(1)
            case, result = res
            print(f"Revalidated case '{case.case_id}' with new status {case.status.value}")
            print(json.dumps({
                "case": case.to_dict(),
                "result": result.to_dict(),
            }, indent=2))

        elif args.subcommand == "explain":
            expl = await svc.get_explanation(args.id)
            if not expl:
                print(f"Error: Explanation for case '{args.id}' not found.", file=sys.stderr)
                sys.exit(1)
            print(json.dumps(expl, indent=2))

        elif args.subcommand == "source":
            src = await svc.get_source(args.id)
            if not src:
                print(f"Error: Source '{args.id}' not found.", file=sys.stderr)
                sys.exit(1)
            print(json.dumps(src.to_dict(), indent=2))

        elif args.subcommand == "lineage":
            lineage = await svc.get_evidence_lineage(args.id)
            print(json.dumps(lineage, indent=2))

        else:
            parser.print_help()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(asyncio.run, run()).result()
    else:
        asyncio.run(run())


if __name__ == "__main__":
    main()
