"""Command-line interface for KAIRO Knowledge Consolidation and Memory Evolution (Task 92 Phase 32).

Usage:
  kairo-memory list [--status <STATUS>] [--type <TYPE>]
  kairo-memory inspect <id>
  kairo-memory history <id>
  kairo-memory evidence <id>
  kairo-memory conflicts
  kairo-memory consolidate <ids...> --summary <SUMMARY>
  kairo-memory revalidate [--capabilities <CAPS>]
  kairo-memory archive <id> [--reason <REASON>]
  kairo-memory forget <id> [--reason <REASON>] [--hard]

  kairo-knowledge reconstruct <query> [--entity <ENTITY>]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.knowledge_consolidation.models import (
    MemoryReconstructionRequest,
    MemoryStatus,
    MemoryType,
)
from app.knowledge_consolidation.service import get_knowledge_consolidation_service


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for memory & knowledge commands."""
    parser = argparse.ArgumentParser(
        prog="kairo-memory",
        description="Kairo Autonomous Knowledge Consolidation & Memory Evolution CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    p_list = subparsers.add_parser("list", help="List active memories")
    p_list.add_argument("--status", choices=[s.value for s in MemoryStatus], help="Filter by status")
    p_list.add_argument("--type", choices=[t.value for t in MemoryType], help="Filter by taxonomy type")
    p_list.add_argument("--include-stale", action="store_true", help="Include stale memories")

    # 2. inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect memory entity details")
    p_inspect.add_argument("memory_id", help="Target memory ID")

    # 3. history
    p_history = subparsers.add_parser("history", help="Inspect immutable lifecycle history")
    p_history.add_argument("memory_id", help="Target memory ID")

    # 4. evidence
    p_evidence = subparsers.add_parser("evidence", help="List grounding evidence for memory")
    p_evidence.add_argument("memory_id", help="Target memory ID")

    # 5. conflicts
    subparsers.add_parser("conflicts", help="List unresolved contradictions")

    # 6. consolidate
    p_consolidate = subparsers.add_parser("consolidate", help="Consolidate episodic memories")
    p_consolidate.add_argument("episode_ids", nargs="+", help="Episodic memory IDs to consolidate")
    p_consolidate.add_argument("--summary", required=True, help="Consolidated semantic summary")

    # 7. revalidate
    p_revalidate = subparsers.add_parser("revalidate", help="Scan and trigger revalidation")
    p_revalidate.add_argument("--capabilities", nargs="*", help="Changed capability identifiers")

    # 8. archive
    p_archive = subparsers.add_parser("archive", help="Archive a memory")
    p_archive.add_argument("memory_id", help="Target memory ID")
    p_archive.add_argument("--reason", default="Archived via CLI", help="Archive reason")

    # 9. forget
    p_forget = subparsers.add_parser("forget", help="Forget a memory with tombstone")
    p_forget.add_argument("memory_id", help="Target memory ID")
    p_forget.add_argument("--reason", default="Forgotten via CLI", help="Forgetting reason")
    p_forget.add_argument("--hard", action="store_true", help="Execute hard deletion")

    # 10. reconstruct
    p_reconstruct = subparsers.add_parser("reconstruct", help="Forensic memory reconstruction")
    p_reconstruct.add_argument("query", help="Reconstruction query")
    p_reconstruct.add_argument("--entity", help="Optional entity focus")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)
    service = get_knowledge_consolidation_service()

    try:
        if args.subcommand == "list":
            st = MemoryStatus(args.status) if args.status else None
            tp = MemoryType(args.type) if args.type else None
            mems = service.list_memories(status=st, type=tp, include_stale=args.include_stale)
            print(json.dumps([m.model_dump() for m in mems], indent=2, default=str))

        elif args.subcommand == "inspect":
            mem = service.get_memory(args.memory_id)
            if not mem:
                print(f"Error: Memory '{args.memory_id}' not found.", file=sys.stderr)
                return 1
            print(json.dumps(mem.model_dump(), indent=2, default=str))

        elif args.subcommand == "history":
            hist = service.lifecycle.get_history(args.memory_id)
            print(json.dumps(hist, indent=2, default=str))

        elif args.subcommand == "evidence":
            evs = service.evidence.get_evidence_for_memory(args.memory_id)
            print(json.dumps([e.model_dump() for e in evs], indent=2, default=str))

        elif args.subcommand == "conflicts":
            cnfs = service.conflicts.list_active_conflicts()
            print(json.dumps([c.model_dump() for c in cnfs], indent=2, default=str))

        elif args.subcommand == "consolidate":
            res = service.consolidate_explicit(args.episode_ids, args.summary)
            print(json.dumps(res, indent=2, default=str))

        elif args.subcommand == "revalidate":
            jobs = service.run_revalidation_scan(args.capabilities)
            print(json.dumps(jobs, indent=2, default=str))

        elif args.subcommand == "archive":
            mem = service.archive_memory(args.memory_id, reason=args.reason)
            print(json.dumps(mem.model_dump(), indent=2, default=str))

        elif args.subcommand == "forget":
            mem = service.forget_memory(args.memory_id, reason=args.reason, hard_delete=args.hard)
            print(json.dumps(mem.model_dump(), indent=2, default=str))

        elif args.subcommand == "reconstruct":
            req = MemoryReconstructionRequest(query=args.query, entity=args.entity)
            res = service.reconstruct(req)
            print(json.dumps(res.model_dump(), indent=2, default=str))

        return 0

    except Exception as exc:
        print(f"Error executing '{args.subcommand}': {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
