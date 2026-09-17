"""KAIRO World-State Reconstruction & Drift Reconciliation CLI (Task 98, Phase 43)."""

import argparse
import asyncio
from datetime import UTC, datetime
import json
import sys

from app.world_state.domain import (
    DriftSeverity,
    DriftStatus,
    WorldScope,
    utc_now,
)
from app.world_state.reconciliation_engine import get_world_state_reconciliation_engine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kairo-state",
        description="Kairo Autonomous World-State Reconstruction & Drift Reconciliation CLI",
    )
    subparsers = parser.add_subparsers(dest="subsystem", help="Subsystem commands")

    # State subcommands
    state_parser = subparsers.add_parser("state", help="World-state inspection and reconciliation")
    state_sub = state_parser.add_subparsers(dest="action", help="State actions")

    # state current
    state_sub.add_parser("current", help="Inspect current reconstructed world state")

    # state inspect <scope>
    inspect_parser = state_sub.add_parser("inspect", help="Inspect state entities in scope")
    inspect_parser.add_argument("scope", type=str, default="SYSTEM", nargs="?", help="Operational scope")

    # state history <scope>
    hist_parser = state_sub.add_parser("history", help="Inspect entity history in scope")
    hist_parser.add_argument("scope", type=str, default="SYSTEM", nargs="?", help="Operational scope")
    hist_parser.add_argument("--entity", type=str, default=None, help="Optional entity ID")

    # state observations <scope>
    obs_parser = state_sub.add_parser("observations", help="Inspect raw ingested observations")
    obs_parser.add_argument("scope", type=str, default="SYSTEM", nargs="?", help="Operational scope")
    obs_parser.add_argument("--limit", type=int, default=20, help="Max observations")

    # state diff <a> <b>
    diff_parser = state_sub.add_parser("diff", help="Compute structural diff between two snapshots")
    diff_parser.add_argument("snapshot_a", type=str, help="First snapshot ID")
    diff_parser.add_argument("snapshot_b", type=str, help="Second snapshot ID")

    # state reconstruct <timestamp>
    recon_parser = state_sub.add_parser("reconstruct", help="Reconstruct historical state at timestamp T")
    recon_parser.add_argument("timestamp", type=str, help="ISO-format timestamp")
    recon_parser.add_argument("--scope", type=str, default="SYSTEM", help="Operational scope")

    # state reconcile <scope>
    rec_parser = state_sub.add_parser("reconcile", help="Reconcile expected vs actual state")
    rec_parser.add_argument("scope", type=str, default="SYSTEM", nargs="?", help="Operational scope")

    # Drift subcommands
    drift_parser = subparsers.add_parser("drift", help="Drift detection and attribution commands")
    drift_sub = drift_parser.add_subparsers(dest="action", help="Drift actions")

    # drift list
    list_parser = drift_sub.add_parser("list", help="List active drift records")
    list_parser.add_argument("--scope", type=str, default="SYSTEM", help="Operational scope")

    # drift inspect <id>
    insp_drift_parser = drift_sub.add_parser("inspect", help="Inspect detailed drift record")
    insp_drift_parser.add_argument("drift_id", type=str, help="Drift record ID")

    # drift analyze <scope>
    analyze_parser = drift_sub.add_parser("analyze", help="Analyze reality drift within scope")
    analyze_parser.add_argument("scope", type=str, default="SYSTEM", nargs="?", help="Operational scope")

    return parser


def main(args: list[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)
    engine = get_world_state_reconciliation_engine()

    if parsed.subsystem == "state":
        if parsed.action == "current":
            entities = list(engine._entities.values())
            print("\nCURRENT WORLD STATE OVERVIEW")
            print("-" * 60)
            print(f"Total Entities:    {len(entities)}")
            print(f"Active Conflicts:  {len(engine._conflicts)}")
            print(f"Active Drifts:     {len(engine._drift_engine._drift_records)}")
            for ent in entities[:10]:
                print(f"  [{ent.status.value:<12}] {ent.entity_id:<32} (freshness={ent.freshness.value}, conf={ent.confidence:.2f})")
            return 0

        elif parsed.action == "inspect":
            scope_val = WorldScope(parsed.scope.upper()) if parsed.scope.upper() in WorldScope.__members__ else WorldScope.SYSTEM
            entities = [e for e in engine._entities.values() if e.scope == scope_val]
            print(f"\nSTATE ENTITIES IN SCOPE [{scope_val.value}] ({len(entities)} entities)")
            print("-" * 60)
            for ent in entities:
                print(f"ID:          {ent.entity_id}")
                print(f"Name:        {ent.canonical_name}")
                print(f"Status:      {ent.status.value} (Epistemic={ent.epistemic_certainty.value})")
                print(f"Confidence:  {ent.confidence:.2f} (Verification={ent.verification_confidence:.2f})")
                print(f"Freshness:   {ent.freshness.value} (Last observed: {ent.last_observed_at.isoformat()})")
                print("-" * 40)
            return 0

        elif parsed.action == "history":
            scope_val = WorldScope(parsed.scope.upper()) if parsed.scope.upper() in WorldScope.__members__ else WorldScope.SYSTEM
            if parsed.entity:
                canonical_id = engine.resolve_canonical_id(parsed.entity)
                hist = engine._entity_history.get(canonical_id, [])
                print(f"\nSTATE MUTATION HISTORY FOR ENTITY [{canonical_id}] ({len(hist)} versions)")
                print("-" * 60)
                for h in hist:
                    print(f"v{h['version']:<3} [{h['timestamp']}] Action: {h['action']:<25} Status: {h['status']}")
            else:
                print(f"\nHISTORY SUMMARY FOR SCOPE [{scope_val.value}]")
                print("-" * 60)
                for eid, hists in engine._entity_history.items():
                    ent = engine._entities.get(eid)
                    if ent and ent.scope == scope_val:
                        print(f"Entity: {eid:<32} History Depth: {len(hists)}")
            return 0

        elif parsed.action == "observations":
            scope_val = WorldScope(parsed.scope.upper()) if parsed.scope.upper() in WorldScope.__members__ else WorldScope.SYSTEM
            obs = [o for o in engine._observations if scope_val == WorldScope.SYSTEM or o.scope == scope_val]
            print(f"\nINGESTED OBSERVATIONS ({len(obs)} records, showing latest {min(len(obs), parsed.limit)})")
            print("-" * 60)
            for o in obs[-parsed.limit:]:
                print(f"[{o.observed_at.isoformat()}] ID: {o.observation_id:<16} Source: {o.source:<16} Entity: {o.entity_id:<24} Value: {o.observed_value}")
            return 0

        elif parsed.action == "diff":
            try:
                diff = engine.compute_diff(parsed.snapshot_a, parsed.snapshot_b)
                print(f"\nSTRUCTURAL STATE DIFF [{parsed.snapshot_a}] -> [{parsed.snapshot_b}]")
                print("-" * 60)
                print(f"Added Entities:    {diff.added_entities}")
                print(f"Removed Entities:  {diff.removed_entities}")
                print(f"Changed Entities:  {len(diff.changed_entities)}")
                for eid, d in diff.changed_entities.items():
                    print(f"  * {eid}: {d}")
                print(f"Unchanged Count:   {len(diff.unchanged_entities)}")
                return 0
            except KeyError as ex:
                print(f"Error: {ex}", file=sys.stderr)
                return 1

        elif parsed.action == "reconstruct":
            try:
                ts = datetime.fromisoformat(parsed.timestamp)
                recon = engine.reconstruct_historical_state(ts)
                print(f"\nHISTORICAL STATE RECONSTRUCTION AT [{parsed.timestamp}]")
                print("-" * 60)
                print(f"Reconstructed Count: {recon['reconstructed_entities_count']}")
                for eid, info in recon["entities"].items():
                    print(f"  * {eid}: {info}")
                return 0
            except Exception as ex:
                print(f"Failed to reconstruct state: {ex}", file=sys.stderr)
                return 1

        elif parsed.action == "reconcile":
            results = asyncio.run(engine.reconcile_expectations())
            print(f"\nEXPECTATION RECONCILIATION COMPLETE")
            print("-" * 60)
            for exp, outcome, drifts in results:
                print(f"Entity: {exp.canonical_id:<32} Outcome: {outcome.value} (Drifts: {len(drifts)})")
            return 0

    elif parsed.subsystem == "drift":
        if parsed.action == "list":
            records = list(engine._drift_engine._drift_records.values())
            print(f"\nACTIVE REALITY DRIFT RECORDS ({len(records)} found)")
            print("-" * 60)
            for d in records:
                print(f"ID:          {d.drift_id}")
                print(f"Entity:      {d.entity_id}")
                print(f"Type:        {d.drift_type.value} | Severity: {d.severity.value}")
                print(f"Class:       {d.classification.value} | Status: {d.status.value}")
                print(f"Attribution: {d.attributed_source_type} ({d.attributed_source_id or 'none'})")
                print(f"Evidence:    {d.evidence[0] if d.evidence else 'No evidence'}")
                print("-" * 40)
            return 0

        elif parsed.action == "inspect":
            d = engine._drift_engine._drift_records.get(parsed.drift_id)
            if not d:
                print(f"Drift record '{parsed.drift_id}' not found.", file=sys.stderr)
                return 1
            print(f"\nDRIFT RECORD [{d.drift_id}]")
            print("-" * 60)
            print(f"Entity:      {d.entity_id} (Scope={d.scope.value})")
            print(f"Type:        {d.drift_type.value}")
            print(f"Severity:    {d.severity.value}")
            print(f"Class:       {d.classification.value}")
            print(f"Expected:    {d.expected_value}")
            print(f"Actual:      {d.actual_value}")
            print(f"Deviation:   {d.deviation_magnitude:.3f}")
            print(f"Causal:      {d.causal_status.value}")
            print(f"Attributed:  {d.attributed_source_type}:{d.attributed_source_id}")
            print(f"Detected At: {d.detected_at.isoformat()}")
            print("Evidence:")
            for ev in d.evidence:
                print(f"  - {ev}")
            return 0

        elif parsed.action == "analyze":
            results = asyncio.run(engine.reconcile_expectations())
            drifts = engine._drift_engine.get_active_drifts()
            print(f"\nREALITY DRIFT ANALYSIS COMPLETED")
            print("-" * 60)
            print(f"Reconciled Expectations: {len(results)}")
            print(f"Detected Drifts:         {len(drifts)}")
            for d in drifts:
                print(f"  * [{d.severity.value:<8}] {d.entity_id:<28} {d.drift_type.value} ({d.classification.value})")
            return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
