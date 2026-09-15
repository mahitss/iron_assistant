"""Command-line interface for the Kairo Capability Lifecycle and Safe Evolution Engine (Task 91 Phase 24).

Usage:
  kairo-capability list [--state <STATE>]
  kairo-capability inspect <id>
  kairo-capability versions <id>
  kairo-capability validate <id>
  kairo-capability conformance <id>
  kairo-capability compatibility <id> --target <version>
  kairo-capability canary <id> --target <version> [--percent <p>]
  kairo-capability promote <id> --target <version>
  kairo-capability rollback <id> [--target <version>]
  kairo-capability deprecate <id> --reason <reason> [--replacement <id>]
  kairo-capability retire <id> [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from app.capability_lifecycle.models import CanaryRolloutConfig, LifecycleState
from app.capability_lifecycle.service import get_capability_lifecycle_service


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser for capability commands."""
    parser = argparse.ArgumentParser(
        prog="kairo-capability",
        description="Kairo Capability Lifecycle, Versioning & Safe Evolution CLI",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 1. list
    list_p = subparsers.add_parser("list", help="List all registered capabilities")
    list_p.add_argument("--state", choices=[s.value for s in LifecycleState], help="Filter by lifecycle state")

    # 2. inspect
    insp_p = subparsers.add_parser("inspect", help="Inspect full capability metadata")
    insp_p.add_argument("capability_id", help="Capability identifier")

    # 3. versions
    ver_p = subparsers.add_parser("versions", help="List immutable version history")
    ver_p.add_argument("capability_id", help="Capability identifier")

    # 4. validate
    val_p = subparsers.add_parser("validate", help="Run validation pipeline on capability")
    val_p.add_argument("capability_id", help="Capability identifier")

    # 5. conformance
    conf_p = subparsers.add_parser("conformance", help="Run deterministic conformance test vectors")
    conf_p.add_argument("capability_id", help="Capability identifier")

    # 6. canary
    can_p = subparsers.add_parser("canary", help="Start progressive canary rollout")
    can_p.add_argument("capability_id", help="Capability identifier")
    can_p.add_argument("--target", required=True, help="Target version string (SemVer)")
    can_p.add_argument("--percent", type=float, default=5.0, help="Initial traffic percentage")

    # 7. promote
    prom_p = subparsers.add_parser("promote", help="Evaluate 11 gates and promote to ACTIVE")
    prom_p.add_argument("capability_id", help="Capability identifier")
    prom_p.add_argument("--target", required=True, help="Target version string (SemVer)")

    # 8. rollback
    rb_p = subparsers.add_parser("rollback", help="Safely roll back capability to stable version")
    rb_p.add_argument("capability_id", help="Capability identifier")
    rb_p.add_argument("--target", default=None, help="Specific target version to roll back to")
    rb_p.add_argument("--reason", default="Manual CLI rollback", help="Rollback reason")

    # 9. deprecate
    dep_p = subparsers.add_parser("deprecate", help="Mark capability as DEPRECATED")
    dep_p.add_argument("capability_id", help="Capability identifier")
    dep_p.add_argument("--reason", required=True, help="Reason for deprecation")
    dep_p.add_argument("--replacement", default=None, help="Replacement capability ID")
    dep_p.add_argument("--days", type=int, default=30, help="Days until sunset deadline")

    # 10. retire
    ret_p = subparsers.add_parser("retire", help="Permanently retire capability")
    ret_p.add_argument("capability_id", help="Capability identifier")
    ret_p.add_argument("--force", action="store_true", help="Bypass active consumer check")

    return parser


def handle_command(args: argparse.Namespace) -> int:
    """Dispatches CLI command to CapabilityLifecycleService."""
    svc = get_capability_lifecycle_service()

    if args.subcommand == "list":
        caps = svc.list_capabilities()
        if args.state:
            caps = [c for c in caps if c.lifecycle_state.value == args.state]
        print(f"Total capabilities: {len(caps)}")
        for c in caps:
            print(f"  * {c.capability_id} (v{c.version}) | State: {c.lifecycle_state.value} | Health: {c.health_state.value}")
        return 0

    elif args.subcommand == "inspect":
        cap = svc.get_capability(args.capability_id)
        if not cap:
            print(f"Error: Capability '{args.capability_id}' not found", file=sys.stderr)
            return 1
        print(json.dumps(cap.model_dump(), indent=2, default=str))
        return 0

    elif args.subcommand == "versions":
        vers = svc.version_manager.list_versions(args.capability_id)
        print(f"Version history for '{args.capability_id}': {len(vers)} records")
        for v in vers:
            active = " [ACTIVE]" if v.is_active else ""
            print(f"  - v{v.version_str} ({v.version_id}){active} | Fingerprint: {v.contract_fingerprint}")
        return 0

    elif args.subcommand == "validate":
        passed, issues = svc.validate_capability(args.capability_id, actor="cli")
        print(f"Validation: {'PASSED' if passed else 'FAILED'}")
        if issues:
            for issue in issues:
                print(f"  ! {issue}")
        return 0 if passed else 1

    elif args.subcommand == "conformance":
        res = svc.test_conformance(args.capability_id)
        print(f"Conformance: {res.passed} passed, {res.failed} failed in {res.duration_ms}ms")
        for detail in res.failure_details:
            print(f"  ! {detail}")
        return 0 if res.failed == 0 else 1

    elif args.subcommand == "canary":
        cfg = CanaryRolloutConfig(canary_percent=args.percent)
        rollout = svc.start_canary(args.capability_id, target_version=args.target, config=cfg, actor="cli")
        print(f"Canary started: {rollout.rollout_id} | Traffic: {rollout.current_percent}% | State: {rollout.state.value}")
        return 0

    elif args.subcommand == "promote":
        promoted, err, gates = svc.promote_capability(args.capability_id, target_version=args.target, actor="cli")
        if promoted:
            print(f"Capability '{args.capability_id}' successfully promoted to ACTIVE at v{args.target}")
            return 0
        print(f"Promotion failed: {err}", file=sys.stderr)
        return 1

    elif args.subcommand == "rollback":
        ok, rec, msg = svc.rollback_capability(
            args.capability_id, target_version=args.target, reason=args.reason, actor="cli"
        )
        print(f"Rollback: {msg} (ID: {rec.rollback_id})")
        return 0 if ok else 1

    elif args.subcommand == "deprecate":
        plan = svc.deprecate_capability(
            args.capability_id,
            reason=args.reason,
            replacement_capability_id=args.replacement,
            sunset_days=args.days,
            actor="cli",
        )
        print(f"Deprecated: Sunset deadline {plan.sunset_deadline.isoformat()}")
        return 0

    elif args.subcommand == "retire":
        ok, msg = svc.retire_capability(args.capability_id, force_retirement=args.force, actor="cli")
        print(f"Retirement: {msg}")
        return 0 if ok else 1

    return 0


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(handle_command(args))


if __name__ == "__main__":
    main()
