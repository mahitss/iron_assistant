"""Command-line interface for Task 110:
Cognitive Working Set, Context Assembly & Lifecycle Engine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.context.working_set_domain import (
    ContextAssemblyRequest,
    ContextQualityAssessment,
    ContextSnapshot,
    WorkingSet,
)
from app.context.working_set_service import WorkingSetService

CLI_CACHE_FILE = Path(tempfile.gettempdir()) / "kairo_context_cli_cache.json"


def _save_cli_cache(ws: WorkingSet, quality: Optional[ContextQualityAssessment] = None, snapshot: Optional[ContextSnapshot] = None) -> None:
    try:
        cache: Dict[str, Any] = {}
        if CLI_CACHE_FILE.exists():
            try:
                cache = json.loads(CLI_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                cache = {}
        cache[ws.working_set_id] = {
            "working_set": json.loads(ws.model_dump_json()),
            "quality": json.loads(quality.model_dump_json()) if quality else None,
            "snapshot": json.loads(snapshot.model_dump_json()) if snapshot else None,
        }
        CLI_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_from_cli_cache(ws_id: str) -> Tuple[Optional[WorkingSet], Optional[ContextQualityAssessment], Optional[ContextSnapshot]]:
    if not CLI_CACHE_FILE.exists():
        return None, None, None
    try:
        cache = json.loads(CLI_CACHE_FILE.read_text(encoding="utf-8"))
        entry = cache.get(ws_id)
        if not entry:
            return None, None, None
        ws = WorkingSet.model_validate(entry["working_set"])
        quality = ContextQualityAssessment.model_validate(entry["quality"]) if entry.get("quality") else None
        snapshot = ContextSnapshot.model_validate(entry["snapshot"]) if entry.get("snapshot") else None
        return ws, quality, snapshot
    except Exception:
        return None, None, None


def _load_all_from_cli_cache() -> List[WorkingSet]:
    if not CLI_CACHE_FILE.exists():
        return []
    try:
        cache = json.loads(CLI_CACHE_FILE.read_text(encoding="utf-8"))
        res = []
        for entry in cache.values():
            if "working_set" in entry:
                res.append(WorkingSet.model_validate(entry["working_set"]))
        return res
    except Exception:
        return []


def _resolve_working_set(service: WorkingSetService, ws_id: str) -> Optional[WorkingSet]:
    ws = service.get_working_set(ws_id)
    if not ws:
        cached_ws, cached_q, cached_snap = _load_from_cli_cache(ws_id)
        if cached_ws:
            service._working_sets[ws_id] = cached_ws
            if cached_q:
                service._quality_assessments[ws_id] = cached_q
            if cached_snap:
                service._snapshots[ws_id] = cached_snap
            ws = cached_ws
    return ws


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairo-context",
        description="Kairo Autonomous Cognitive Working Set & Context Lifecycle CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # assemble
    p_assemble = subparsers.add_parser("assemble", help="Assemble a new cognitive working set")
    p_assemble.add_argument("--objective", required=True, help="Task objective or query")
    p_assemble.add_argument("--operation-type", default="DELIBERATION", help="Cognitive operation type")
    p_assemble.add_argument("--token-budget", type=int, default=8000, help="Max token capacity")
    p_assemble.add_argument("--user-scope", default="default_user", help="User scope")

    # list
    p_list = subparsers.add_parser("list", help="List active working sets")
    p_list.add_argument("--user-scope", default="default_user", help="User scope")

    # show
    p_show = subparsers.add_parser("show", help="Show working set overview")
    p_show.add_argument("id", help="Working set ID")

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect all items in a working set")
    p_inspect.add_argument("id", help="Working set ID")

    # provenance
    p_prov = subparsers.add_parser("provenance", help="View item provenance chains")
    p_prov.add_argument("id", help="Working set ID")

    # conflicts
    p_conflicts = subparsers.add_parser("conflicts", help="View preserved conflicts")
    p_conflicts.add_argument("id", help="Working set ID")

    # gaps
    p_gaps = subparsers.add_parser("gaps", help="View missing context gaps")
    p_gaps.add_argument("id", help="Working set ID")

    # refresh
    p_refresh = subparsers.add_parser("refresh", help="Refresh and revalidate working set")
    p_refresh.add_argument("id", help="Working set ID")

    # invalidate
    p_inv = subparsers.add_parser("invalidate", help="Invalidate working set fail-closed")
    p_inv.add_argument("id", help="Working set ID")
    p_inv.add_argument("--reason", default="CLI requested invalidation", help="Invalidation reason")

    # quality
    p_quality = subparsers.add_parser("quality", help="View 13-dimension quality assessment")
    p_quality.add_argument("id", help="Working set ID")

    # snapshot
    p_snap = subparsers.add_parser("snapshot", help="View immutable audit snapshot")
    p_snap.add_argument("id", help="Working set ID")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    service = WorkingSetService.get_instance()

    if args.command == "assemble":
        req = ContextAssemblyRequest(
            objective=args.objective,
            operation_type=args.operation_type,
            token_budget=args.token_budget,
            user_scope=args.user_scope,
        )
        ws = service.assemble_working_set(req)
        q = service.get_quality_assessment(ws.working_set_id)
        snap = service.get_snapshot(ws.working_set_id)
        _save_cli_cache(ws, q, snap)
        print(json.dumps({
            "status": "SUCCESS",
            "working_set_id": ws.working_set_id,
            "lifecycle": ws.lifecycle.value,
            "version": ws.version,
            "item_count": ws.item_count,
            "total_tokens": ws.total_tokens,
            "quality_score": ws.quality_score,
            "trace_id": ws.trace_id,
        }, indent=2))

    elif args.command == "list":
        sets = service.list_working_sets(user_scope=args.user_scope)
        if not sets:
            cached = _load_all_from_cli_cache()
            sets = [c for c in cached if c.user_scope == args.user_scope]
        print(json.dumps([
            {
                "working_set_id": w.working_set_id,
                "version": w.version,
                "operation_type": w.operation_type,
                "lifecycle": w.lifecycle.value,
                "items": w.item_count,
                "tokens": w.total_tokens,
                "created_at": w.created_at.isoformat(),
            }
            for w in sets
        ], indent=2))

    elif args.command == "show":
        ws = _resolve_working_set(service, args.id)
        if not ws:
            print(f"Error: Working set '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps({
            "working_set_id": ws.working_set_id,
            "version": ws.version,
            "lifecycle": ws.lifecycle.value,
            "objective": ws.objective,
            "operation_type": ws.operation_type,
            "item_count": ws.item_count,
            "total_tokens": ws.total_tokens,
            "conflicts_count": len(ws.conflicts),
            "gaps_count": len(ws.gaps),
            "quality_score": ws.quality_score,
            "completeness_estimate": ws.completeness_estimate,
            "lease_state": ws.lease.state.value if ws.lease else "NONE",
        }, indent=2))

    elif args.command == "inspect":
        ws = _resolve_working_set(service, args.id)
        if not ws:
            print(f"Error: Working set '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        items = [
            {
                "item_id": i.item_id,
                "section": i.section.value,
                "title": i.title,
                "inclusion": i.inclusion.value,
                "relevance": i.relevance_score,
                "freshness": i.freshness.classification.value,
                "tokens": i.token_estimate,
                "is_untrusted": i.is_untrusted,
            }
            for sec in ws.sections.values()
            for i in sec.items
        ]
        print(json.dumps(items, indent=2))

    elif args.command == "provenance":
        ws = _resolve_working_set(service, args.id)
        if not ws:
            print(f"Error: Working set '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        prov = [
            {
                "item_id": i.item_id,
                "source": i.provenance.source_type,
                "trust_label": i.provenance.trust_label.value,
                "lineage": i.provenance.lineage_path,
                "signature": i.provenance.signature,
            }
            for sec in ws.sections.values()
            for i in sec.items
        ]
        print(json.dumps(prov, indent=2))

    elif args.command == "conflicts":
        ws = _resolve_working_set(service, args.id)
        if not ws:
            print(f"Error: Working set '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([c.model_dump(mode="json") for c in ws.conflicts], indent=2))

    elif args.command == "gaps":
        ws = _resolve_working_set(service, args.id)
        if not ws:
            print(f"Error: Working set '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps([g.model_dump(mode="json") for g in ws.gaps], indent=2))

    elif args.command == "refresh":
        ws = _resolve_working_set(service, args.id)
        if not ws:
            print(f"Error: Working set '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        try:
            updated = service.refresh_working_set(args.id)
            q = service.get_quality_assessment(updated.working_set_id)
            snap = service.get_snapshot(updated.working_set_id)
            _save_cli_cache(updated, q, snap)
            print(json.dumps({"status": "REFRESHED", "version": updated.version}, indent=2))
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "invalidate":
        ws = _resolve_working_set(service, args.id)
        if not ws:
            print(f"Error: Working set '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        try:
            inv = service.invalidate_working_set(args.id, reason=args.reason)
            q = service.get_quality_assessment(inv.working_set_id)
            snap = service.get_snapshot(inv.working_set_id)
            _save_cli_cache(inv, q, snap)
            print(json.dumps({"status": "INVALIDATED", "lifecycle": inv.lifecycle.value}, indent=2))
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "quality":
        _resolve_working_set(service, args.id)
        q = service.get_quality_assessment(args.id)
        if not q:
            print(f"Error: Quality assessment for '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(q.model_dump(mode="json"), indent=2))

    elif args.command == "snapshot":
        _resolve_working_set(service, args.id)
        snap = service.get_snapshot(args.id)
        if not snap:
            print(f"Error: Snapshot for '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        print(json.dumps(snap.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
