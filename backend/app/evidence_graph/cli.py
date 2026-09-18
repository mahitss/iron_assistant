"""CLI subcommands for Task 117 (Section 45):
Kairo Autonomous Evidence Graph, Provenance Intelligence & Verification Dependency Engine.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import List, Optional

from app.evidence_graph.service import get_evidence_graph_service


def main(args_list: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="kairo evidence",
        description="Autonomous Evidence Graph & Provenance Intelligence CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Evidence Graph subcommands")

    # 1. graph
    graph_parser = subparsers.add_parser("graph", help="Display summary or list of evidence graph nodes")
    graph_parser.add_argument("--type", default=None, help="Filter by node type")
    graph_parser.add_argument("--limit", type=int, default=50, help="Max nodes")
    graph_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 2. lineage <node_id>
    lineage_parser = subparsers.add_parser("lineage", help="Display minimal sufficient provenance chain for a node")
    lineage_parser.add_argument("id", help="Node ID")
    lineage_parser.add_argument("--max-depth", type=int, default=10, help="Max traversal depth")
    lineage_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 3. upstream <node_id>
    upstream_parser = subparsers.add_parser("upstream", help="Traverse upstream dependencies")
    upstream_parser.add_argument("id", help="Node ID")
    upstream_parser.add_argument("--depth", type=int, default=8, help="Max traversal depth")
    upstream_parser.add_argument("--as-of", default=None, help="Historical as-of ISO timestamp")
    upstream_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 4. downstream <node_id>
    downstream_parser = subparsers.add_parser("downstream", help="Traverse downstream dependents")
    downstream_parser.add_argument("id", help="Node ID")
    downstream_parser.add_argument("--depth", type=int, default=8, help="Max traversal depth")
    downstream_parser.add_argument("--as-of", default=None, help="Historical as-of ISO timestamp")
    downstream_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 5. impact <node_id>
    impact_parser = subparsers.add_parser("impact", help="Assess blast-radius impact of node invalidation")
    impact_parser.add_argument("id", help="Node ID")
    impact_parser.add_argument("--reason", default="CLI blast-radius evaluation", help="Reason for evaluation")
    impact_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 6. gaps
    gaps_parser = subparsers.add_parser("gaps", help="List detected provenance gaps")
    gaps_parser.add_argument("--node-id", default=None, help="Filter by affected node ID")
    gaps_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 7. cycles
    cycles_parser = subparsers.add_parser("cycles", help="Detect circular provenance dependencies")
    cycles_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 8. concentration <node_id>
    conc_parser = subparsers.add_parser("concentration", help="Analyze source concentration / shared origin")
    conc_parser.add_argument("id", help="Node ID")
    conc_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 9. fragility <node_id>
    frag_parser = subparsers.add_parser("fragility", help="Compute multi-dimensional evidence fragility")
    frag_parser.add_argument("id", help="Node ID")
    frag_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 10. snapshot
    snap_parser = subparsers.add_parser("snapshot", help="Create an immutable point-in-time snapshot")
    snap_parser.add_argument("--reason", default="CLI snapshot", help="Reason for snapshot")
    snap_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 11. diff <base_id> <target_id>
    diff_parser = subparsers.add_parser("diff", help="Compute graph diff between two snapshots")
    diff_parser.add_argument("base", help="Base snapshot ID")
    diff_parser.add_argument("target", help="Target snapshot ID")
    diff_parser.add_argument("--json", action="store_true", help="Output JSON")

    # 12. revalidation
    reval_parser = subparsers.add_parser("revalidation", help="List active revalidation queue candidates")
    reval_parser.add_argument("--limit", type=int, default=50, help="Max candidates")
    reval_parser.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args(args_list)
    if not args.subcommand:
        parser.print_help()
        return

    svc = get_evidence_graph_service()

    if args.subcommand == "graph":
        nodes = svc.list_nodes(node_type=args.type, limit=args.limit)
        if args.json:
            print(json.dumps([n.to_dict() for n in nodes], indent=2))
        else:
            print(f"Evidence Graph Nodes ({len(nodes)}):")
            for n in nodes:
                print(f"  [{n.node_type.value}] {n.node_id} (version={n.version}, freshness={n.freshness_state.value})")

    elif args.subcommand == "lineage":
        res = svc.get_minimal_chain(node_id=args.id, max_depth=args.max_depth)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Minimal Lineage for {args.id} ({res.get('chain_type')}):")
            for n in res.get("nodes", []):
                print(f"  -> [{n['node_type']}] {n['node_id']}")
            print(f"Root Sources: {res.get('root_sources')}")

    elif args.subcommand == "upstream":
        res = svc.get_upstream(node_id=args.id, max_depth=args.depth, as_of=args.as_of)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Upstream Dependencies for {args.id} (depth={res['depth_reached']}, status={res['status']}):")
            for n in res["nodes"]:
                print(f"  - [{n['node_type']}] {n['node_id']}")

    elif args.subcommand == "downstream":
        res = svc.get_downstream(node_id=args.id, max_depth=args.depth, as_of=args.as_of)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(f"Downstream Dependents for {args.id} (depth={res['depth_reached']}, status={res['status']}):")
            for n in res["nodes"]:
                print(f"  - [{n['node_type']}] {n['node_id']}")

    elif args.subcommand == "impact":
        res = asyncio.run(svc.assess_blast_radius(node_id=args.id, cause_reason=args.reason))
        if args.json:
            print(json.dumps(res.to_dict(), indent=2))
        else:
            print(f"Blast Radius for {args.id} (Severity: {res.severity.value}):")
            print(f"  Direct Impacts: {len(res.direct_impacts)}")
            print(f"  Indirect Impacts: {len(res.indirect_impacts)}")
            print(f"  Impacted Decisions: {res.impacted_decisions}")
            print(f"  Impacted Missions: {res.impacted_missions}")
            print(f"  Revalidation Candidates: {len(res.revalidation_candidates)}")

    elif args.subcommand == "gaps":
        gaps = svc.list_provenance_gaps(node_id=args.node_id)
        if args.json:
            print(json.dumps([g.to_dict() for g in gaps], indent=2))
        else:
            print(f"Provenance Gaps ({len(gaps)}):")
            for g in gaps:
                print(f"  [{g.severity.value}] Node {g.affected_node_id} lacks {g.missing_relationship}: {g.reason}")

    elif args.subcommand == "cycles":
        cycles = svc.detect_cycles()
        if args.json:
            print(json.dumps(cycles, indent=2))
        else:
            print(f"Circular Provenance Checks ({len(cycles)} detected):")
            for c in cycles:
                print(f"  [CIRCULAR] {c['cycle_repr']}")

    elif args.subcommand == "concentration":
        finding = svc.analyze_source_concentration(args.id)
        if args.json:
            print(json.dumps(finding.to_dict(), indent=2))
        else:
            print(f"Source Concentration for {args.id}:")
            print(f"  Origins: {finding.origin_count}, Depth: {finding.dependency_depth}")
            print(f"  High Concentration: {finding.is_high_concentration}")
            print(f"  Details: {finding.details}")

    elif args.subcommand == "fragility":
        frag = svc.assess_fragility(args.id)
        if args.json:
            print(json.dumps(frag.to_dict(), indent=2))
        else:
            print(f"Evidence Fragility for {args.id} (Overall: {frag.overall_fragility_label}):")
            print(f"  Source Concentration Score: {frag.source_concentration_score}")
            print(f"  Completeness Score: {frag.provenance_completeness_score}")
            print(f"  Single-Source Dependent: {frag.single_source_dependence}")
            print(f"  Unresolved Gaps: {frag.unresolved_gaps_count}")

    elif args.subcommand == "snapshot":
        snap = asyncio.run(svc.create_snapshot(reason=args.reason))
        if args.json:
            print(json.dumps(snap.to_dict(), indent=2))
        else:
            print(f"Snapshot Created: {snap.snapshot_id}")
            print(f"  Checksum: {snap.checksum}")
            print(f"  Nodes: {snap.node_count}, Edges: {snap.edge_count}")

    elif args.subcommand == "diff":
        diff = svc.diff_snapshots(args.base, args.target)
        if not diff:
            print("Error: Snapshot not found.", file=sys.stderr)
            sys.exit(1)
        if args.json:
            print(json.dumps(diff.to_dict(), indent=2))
        else:
            print(f"Graph Diff ({args.base} -> {args.target}):")
            print(f"  Added Nodes: {len(diff.added_nodes)}, Removed: {len(diff.removed_nodes)}, Changed: {len(diff.changed_nodes)}")
            print(f"  Added Edges: {len(diff.added_edges)}, Removed: {len(diff.removed_edges)}")
            print(f"  Invalidated: {len(diff.invalidated_nodes)}, Stale: {len(diff.stale_nodes)}")

    elif args.subcommand == "revalidation":
        candidates = svc.list_revalidation_candidates(limit=args.limit)
        if args.json:
            print(json.dumps([c.to_dict() for c in candidates], indent=2))
        else:
            print(f"Revalidation Queue Candidates ({len(candidates)}):")
            for c in candidates:
                print(f"  [{c.severity.value}] {c.candidate_id}: Node {c.affected_node_id} ({c.recommended_next_step.value}) - {c.reason}")


if __name__ == "__main__":
    main()
