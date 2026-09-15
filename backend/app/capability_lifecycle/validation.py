"""Multi-phase capability validation pipeline (Task 91 Phase 6)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.capability_lifecycle.dependency_graph import CapabilityDependencyGraph, get_capability_dependency_graph
from app.capability_lifecycle.fingerprinting import CapabilityFingerprinter
from app.capability_lifecycle.models import (
    CapabilityMetadata,
    LifecycleState,
    SecurityClassification,
    _now_utc,
)
from app.capability_lifecycle.state_machine import CapabilityStateMachine, get_capability_state_machine
from app.capability_lifecycle.versioning import parse_semver

logger = logging.getLogger("kairo.capability_lifecycle.validation")


class CapabilityValidator:
    """Validates capability integrity, schema conformance, dependencies, and security classification."""

    def __init__(
        self,
        state_machine: Optional[CapabilityStateMachine] = None,
        dependency_graph: Optional[CapabilityDependencyGraph] = None,
    ) -> None:
        self.state_machine = state_machine or get_capability_state_machine()
        self.dependency_graph = dependency_graph or get_capability_dependency_graph()

    def validate_capability(
        self,
        capability: CapabilityMetadata,
        available_target_versions: Optional[Dict[str, str]] = None,
        actor: str = "validator",
    ) -> Tuple[bool, List[str]]:
        """Executes full validation suite. Does NOT activate or grant security permissions."""
        issues: List[str] = []

        # 1. State machine transition to VALIDATING
        if capability.lifecycle_state in (LifecycleState.DISCOVERED, LifecycleState.FAILED, LifecycleState.BLOCKED):
            try:
                self.state_machine.transition(
                    capability,
                    LifecycleState.VALIDATING,
                    reason="Starting formal capability validation checks",
                    actor=actor,
                )
            except Exception as e:
                issues.append(f"State transition to VALIDATING failed: {e}")
                return False, issues

        # 2. Metadata & SemVer Syntax Check
        if not capability.capability_id or len(capability.capability_id.strip()) < 3:
            issues.append("Capability ID must be at least 3 characters")
        if not capability.name or len(capability.name.strip()) < 2:
            issues.append("Capability name is missing or too short")

        try:
            parse_semver(capability.version)
        except Exception as e:
            issues.append(f"Invalid SemVer: {e}")

        # 3. Schema Structure Check
        if not isinstance(capability.parameters_schema, dict):
            issues.append("parameters_schema must be a valid dictionary")
        elif "type" in capability.parameters_schema and capability.parameters_schema["type"] != "object":
            issues.append("Top-level parameters_schema type must be 'object'")

        # 4. Resource Profile Boundaries Check
        res = capability.resource_profile
        if res.memory_mb <= 0 or res.memory_mb > 16384.0:
            issues.append(f"Resource memory_mb must be between 1 and 16384 MB (got {res.memory_mb})")
        if res.cpu_cores <= 0 or res.cpu_cores > 32.0:
            issues.append(f"Resource cpu_cores must be between 0.1 and 32 (got {res.cpu_cores})")
        if res.timeout_seconds <= 0 or res.timeout_seconds > 600.0:
            issues.append(f"Resource timeout_seconds must be between 1 and 600s (got {res.timeout_seconds})")

        # 5. Security Permissions Declaration Check
        valid_perms = {"READ", "WRITE", "EXECUTE", "EXTERNAL", "DESTRUCTIVE"}
        for p in capability.required_permissions:
            if p.upper() not in valid_perms:
                issues.append(f"Invalid permission '{p}'. Allowed: {sorted(valid_perms)}")

        # 6. Dependency Availability Check
        if available_target_versions is not None:
            deps_ok, dep_errs = self.dependency_graph.validate_dependency_versions(
                capability.capability_id, available_target_versions
            )
            if not deps_ok:
                issues.extend(dep_errs)

        # 7. Fingerprint Integrity & Calculation
        CapabilityFingerprinter.fingerprint_capability(capability)
        int_ok, int_err = CapabilityFingerprinter.verify_fingerprint_integrity(capability)
        if not int_ok:
            issues.append(int_err or "Fingerprint verification failed")

        capability.last_validated_at = _now_utc()
        passed = len(issues) == 0

        # 8. State machine transition to VALIDATED or FAILED
        target_state = LifecycleState.VALIDATED if passed else LifecycleState.FAILED
        reason = "All validation checks passed successfully" if passed else f"Validation failed with {len(issues)} issues"
        self.state_machine.transition(
            capability,
            target_state,
            reason=reason,
            actor=actor,
            safety_metadata={"issues": issues, "passed": passed},
        )

        logger.info(
            "Capability '%s' validation %s (Issues: %d)",
            capability.capability_id,
            "PASSED" if passed else "FAILED",
            len(issues),
        )
        return passed, issues


_global_validator: Optional[CapabilityValidator] = None


def get_capability_validator() -> CapabilityValidator:
    global _global_validator
    if _global_validator is None:
        _global_validator = CapabilityValidator()
    return _global_validator
