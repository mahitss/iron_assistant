"""Command-line interface for Task 111:
KAIRO Autonomous Temporal Intelligence, Event History, Change Reconstruction & "What Changed?" Engine.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import sys
from typing import Any

from app.temporal.domain import (
    TemporalEntityType,
    TemporalQuery,
    utc_now,
)
from app.temporal.service import TemporalIntelligenceService


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kairo-temporal",
        description="Kairo Autonomous Temporal Intelligence CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available temporal subcommands")

    # 1. timeline <entity>
    p_timeline = subparsers.add_parser("timeline", help="Inspect timeline for an entity")
    p_timeline.add_argument("entity", nargs="?", default="global", help="Entity ID (or 'global')")
    p_timeline.add_argument("--limit", type=int, default=50, help="Max entries")

    # 2. changes [entity]
    p_changes = subparsers.add_parser("changes", help="View recent change sets")
    p_changes.add_argument("entity", nargs="?", default=None, help="Entity ID (optional)")
    p_changes.add_argument("--limit", type=int, default=10, help="Max changesets")

    # 3. state <entity>
    p_state = subparsers.add_parser("state", help="Inspect current state of an entity")
    p_state.add_argument("entity", help="Entity ID")

    # 4. state-at <entity> <timestamp>
    p_state_at = subparsers.add_parser("state-at", help="Evaluate historical state as-of timestamp")
    p_state_at.add_argument("entity", help="Entity ID")
    p_state_at.add_argument("timestamp", help="ISO format timestamp (e.g. 2026-09-18T05:00:00Z)")

    # 5. diff <checkpoint_a|json> <checkpoint_b|json>
    p_diff = subparsers.add_parser("diff", help="Compute semantic 'What Changed?' between two checkpoints or states")
    p_diff.add_argument("checkpoint_a", help="First checkpoint ID, name, or JSON string")
    p_diff.add_argument("checkpoint_b", help="Second checkpoint ID, name, or JSON string")

    # 6. gaps
    subparsers.add_parser("gaps", help="List unobserved temporal gaps")

    # 7. anomalies
    subparsers.add_parser("anomalies", help="List detected temporal anomalies")

    # 8. watermarks
    subparsers.add_parser("watermarks", help="List active subsystem watermarks")

    # 9. checkpoint <name>
    p_chkp = subparsers.add_parser("checkpoint", help="Capture a new temporal checkpoint")
    p_chkp.add_argument("name", help="Checkpoint identifier or name")

    # 10. reconstruct [from_time] [to_time]
    p_recon = subparsers.add_parser("reconstruct", help="Trigger offline period reconciliation")
    p_recon.add_argument("from_time", nargs="?", default=None, help="Start time ISO (optional)")
    p_recon.add_argument("to_time", nargs="?", default=None, help="End time ISO (optional)")
    p_recon.add_argument("--subsystem", default="telemetry", help="Target subsystem")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    svc = TemporalIntelligenceService.get_instance()

    if args.command == "timeline":
        ent = None if args.entity == "global" else args.entity
        tl = svc.get_timeline(entity_id=ent)
        events = [e for seg in tl.segments for e in seg.events][:args.limit]
        transitions = [t for seg in tl.segments for t in seg.transitions][:args.limit]
        print(json.dumps({
            "timeline_id": tl.timeline_id,
            "entity_id": tl.entity_id,
            "total_events": tl.total_events,
            "total_transitions": tl.total_transitions,
            "events": [e.model_dump(mode="json") for e in events],
            "transitions": [t.model_dump(mode="json") for t in transitions],
        }, indent=2))

    elif args.command == "changes":
        sets = sorted(svc._changesets.values(), key=lambda c: c.created_at, reverse=True)
        if args.entity:
            filtered_sets = []
            for s in sets:
                matching = [c for c in s.changes if c.entity_id == args.entity]
                if matching:
                    s_copy = s.model_copy(update={"changes": matching})
                    filtered_sets.append(s_copy)
            sets = filtered_sets
        print(json.dumps([c.model_dump(mode="json") for c in sets[:args.limit]], indent=2))

    elif args.command == "state":
        ent = svc._entities.get(args.entity)
        if not ent:
            res = svc.state_as_of(args.entity, as_of_time=utc_now())
            print(json.dumps(res, indent=2))
        else:
            print(json.dumps(ent.model_dump(mode="json"), indent=2))

    elif args.command == "state-at":
        try:
            ts = datetime.fromisoformat(args.timestamp.replace("Z", "+00:00"))
        except Exception:
            print(f"Error: Invalid ISO timestamp '{args.timestamp}'", file=sys.stderr)
            sys.exit(1)
        res = svc.state_as_of(args.entity, as_of_time=ts)
        print(json.dumps(res, indent=2))

    elif args.command == "diff":
        # Check if arguments are JSON dict strings
        handled = False
        try:
            state_a = json.loads(args.checkpoint_a)
            state_b = json.loads(args.checkpoint_b)
            if isinstance(state_a, dict) and isinstance(state_b, dict):
                cs = svc.compute_diff(state_a, state_b, from_reference="arg_a", to_reference="arg_b")
                print(json.dumps(cs.model_dump(mode="json"), indent=2))
                handled = True
        except Exception:
            handled = False

        if not handled:
            try:
                cs = svc.diff_checkpoints(args.checkpoint_a, args.checkpoint_b)
                print(json.dumps(cs.model_dump(mode="json"), indent=2))
            except KeyError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                sys.exit(1)

    elif args.command == "gaps":
        gaps = svc.list_gaps()
        print(json.dumps([g.model_dump(mode="json") for g in gaps], indent=2))

    elif args.command == "anomalies":
        anoms = svc.list_anomalies()
        print(json.dumps([a.model_dump(mode="json") for a in anoms], indent=2))

    elif args.command == "watermarks":
        wm = svc.list_watermarks()
        print(json.dumps([w.model_dump(mode="json") for w in wm], indent=2))

    elif args.command == "checkpoint":
        chkp = svc.create_checkpoint(name=args.name, creator="cli")
        print(json.dumps(chkp.model_dump(mode="json"), indent=2))

    elif args.command == "reconstruct":
        reconnect_t = utc_now()
        if args.to_time:
            try:
                reconnect_t = datetime.fromisoformat(args.to_time.replace("Z", "+00:00"))
            except Exception:
                pass
        cs, gaps = svc.reconcile_offline(
            subsystem=args.subsystem,
            prior_state={},
            observed_current_state={"system_health": "READY"},
            reconnect_time=reconnect_t,
        )
        print(json.dumps({
            "status": "RECONCILED",
            "changes_detected": len(cs.changes),
            "gaps_recorded": len(gaps),
        }, indent=2))


if __name__ == "__main__":
    main()
