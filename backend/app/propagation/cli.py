"""Command-line interface for risk propagation and cascade analysis (Spec 79)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List

from app.propagation.schemas import TriggerType
from app.propagation.service import default_propagation_service
from app.propagation.snapshots import default_snapshot_engine


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for kairo propagation commands (Spec 79)."""
    parser = argparse.ArgumentParser(
        prog="kairo propagation",
        description="Kairo Autonomous Risk Propagation & Cascade Analysis CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze command
    analyze_p = subparsers.add_parser("analyze", help="Run propagation analysis for a trigger component")
    analyze_p.add_argument("origin_entity", help="Component or service ID initiating propagation")
    analyze_p.add_argument("--trigger", "-t", default="Manual CLI trigger", help="Trigger description")
    analyze_p.add_argument("--type", default="STATE_CHANGE", choices=[t.value for t in TriggerType], help="Trigger type")
    analyze_p.add_argument("--tenant", default="default_tenant", help="Tenant ID")

    # inspect command
    inspect_p = subparsers.add_parser("inspect", help="Inspect an existing propagation analysis")
    inspect_p.add_argument("analysis_id", help="Propagation analysis UUID")

    # graph command
    graph_p = subparsers.add_parser("graph", help="Display topological propagation graph")
    graph_p.add_argument("analysis_id", help="Propagation analysis UUID")

    # cascades command
    cascades_p = subparsers.add_parser("cascades", help="List active projected cascades")
    cascades_p.add_argument("--tenant", default="default_tenant", help="Tenant ID")

    # bottlenecks command
    bottlenecks_p = subparsers.add_parser("bottlenecks", help="List detected systemic bottlenecks")
    bottlenecks_p.add_argument("--tenant", default="default_tenant", help="Tenant ID")

    # resilience command
    resilience_p = subparsers.add_parser("resilience", help="View systemic resilience metrics")
    resilience_p.add_argument("--tenant", default="default_tenant", help="Tenant ID")

    return parser


def handle_analyze(args: argparse.Namespace) -> int:
    """Execute propagation analysis from CLI."""
    analysis = default_propagation_service.analyze_propagation(
        origin_entity=args.origin_entity,
        trigger=args.trigger,
        trigger_type=TriggerType(args.type),
        tenant_id=args.tenant,
    )
    print(f"=== PROPAGATION ANALYSIS: {analysis.propagation_id} ===")
    print(f"Origin Entity: {analysis.origin_entity}")
    print(f"Trigger: {analysis.trigger} ({analysis.trigger_type.value})")
    print(f"Propagation Depth: {analysis.propagation_depth}")
    print(f"Confidence: {analysis.confidence:.2f}")
    print(f"Direct Effects: {len(analysis.direct_effects)}")
    print(f"Second-Order Effects: {len(analysis.second_order_effects)}")
    print(f"Cascades Detected: {len(analysis.cascades)}")
    print(f"Resilience Score: {analysis.resilience_assessment.systemic_resilience_score:.2f}")
    return 0


def handle_inspect(args: argparse.Namespace) -> int:
    """Inspect analysis details."""
    analysis = default_propagation_service.get_analysis(args.analysis_id)
    if not analysis:
        print(f"Error: Propagation analysis '{args.analysis_id}' not found.", file=sys.stderr)
        return 1

    print(json.dumps(analysis.model_dump(mode="json"), indent=2))
    return 0


def handle_cascades(args: argparse.Namespace) -> int:
    """List active cascades."""
    cascades = default_propagation_service.list_active_cascades(tenant_id=args.tenant)
    print(f"=== ACTIVE CASCADES ({len(cascades)}) ===")
    for c in cascades:
        print(f"[{c.cascade_type.value}] {' -> '.join(c.nodes)} | Likelihood: {c.likelihood:.2f} | Delay: {c.cumulative_delay_seconds:.1f}s")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI execution dispatcher."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return handle_analyze(args)
    elif args.command == "inspect":
        return handle_inspect(args)
    elif args.command == "cascades":
        return handle_cascades(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
