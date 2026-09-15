"""Semantic versioning, lineage tracking, and immutability management for capabilities (Task 91 Phase 3)."""

from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Tuple

from app.capability_lifecycle.models import (
    CapabilityMetadata,
    CapabilityVersionRecord,
    generate_cl_id,
    _now_utc,
)

logger = logging.getLogger("kairo.capability_lifecycle.versioning")

SEMVER_REGEX = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)(?:-(?P<prerelease>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$"
)


class VersionParseError(Exception):
    """Raised when a version string fails SemVer syntax validation."""


class ImmutableVersionMutationError(Exception):
    """Raised when attempting to modify an immutable active capability version."""


def parse_semver(version_str: str) -> Tuple[int, int, int, str]:
    """Extracts major, minor, patch, and build metadata from a SemVer string."""
    m = SEMVER_REGEX.match(version_str.strip())
    if not m:
        raise VersionParseError(f"Invalid semantic version string: '{version_str}' (expected format: X.Y.Z)")
    major = int(m.group("major"))
    minor = int(m.group("minor"))
    patch = int(m.group("patch"))
    build = m.group("build") or ""
    return major, minor, patch, build


def compare_semver(v1: str, v2: str) -> int:
    """Returns > 0 if v1 > v2, < 0 if v1 < v2, 0 if v1 == v2."""
    maj1, min1, pat1, _ = parse_semver(v1)
    maj2, min2, pat2, _ = parse_semver(v2)
    if (maj1, min1, pat1) > (maj2, min2, pat2):
        return 1
    elif (maj1, min1, pat1) < (maj2, min2, pat2):
        return -1
    return 0


def satisfies_constraint(version_str: str, constraint_str: str) -> bool:
    """Evaluates whether version_str satisfies a basic SemVer constraint (e.g. '>=1.0.0', '^1.2', '*')."""
    constraint = constraint_str.strip()
    if constraint in ("*", "", "any"):
        return True

    # Check >= operator
    if constraint.startswith(">="):
        target = constraint[2:].strip()
        return compare_semver(version_str, target) >= 0
    # Check > operator
    if constraint.startswith(">"):
        target = constraint[1:].strip()
        return compare_semver(version_str, target) > 0
    # Check <= operator
    if constraint.startswith("<="):
        target = constraint[2:].strip()
        return compare_semver(version_str, target) <= 0
    # Check < operator
    if constraint.startswith("<"):
        target = constraint[1:].strip()
        return compare_semver(version_str, target) < 0
    # Check == or exact
    exact = constraint[2:].strip() if constraint.startswith("==") else constraint
    return compare_semver(version_str, exact) == 0


class CapabilityVersionManager:
    """Manages immutable version records, lineage, and version promotion."""

    def __init__(self) -> None:
        # capability_id -> list of CapabilityVersionRecord
        self._versions: Dict[str, List[CapabilityVersionRecord]] = {}

    def register_version(
        self,
        capability: CapabilityMetadata,
        source_revision: str = "HEAD",
    ) -> CapabilityVersionRecord:
        """Creates an immutable version record for a capability."""
        cap_id = capability.capability_id
        major, minor, patch, build = parse_semver(capability.version)

        # Ensure version not already recorded
        existing = self.get_version(cap_id, capability.version)
        if existing is not None:
            if existing.is_active:
                raise ImmutableVersionMutationError(
                    f"Version '{capability.version}' of capability '{cap_id}' is active and immutable. "
                    "You must increment the version number to publish modifications."
                )
            return existing

        # Determine lineage (supersedes previous latest version)
        all_versions = self.list_versions(cap_id)
        superseded_id = all_versions[-1].version_id if all_versions else None

        rec = CapabilityVersionRecord(
            version_id=generate_cl_id("ver"),
            capability_id=cap_id,
            version_str=capability.version,
            major=major,
            minor=minor,
            patch=patch,
            build_metadata=build,
            source_revision=source_revision,
            contract_fingerprint=capability.contract_fingerprint,
            implementation_fingerprint=capability.implementation_fingerprint,
            dependency_fingerprint=capability.composite_fingerprint,
            supersedes=superseded_id,
            is_active=False,
        )

        if superseded_id and all_versions:
            all_versions[-1].superseded_by = rec.version_id

        self._versions.setdefault(cap_id, []).append(rec)
        logger.info(
            "Registered immutable capability version: %s v%s (%s)",
            cap_id,
            capability.version,
            rec.version_id,
        )
        return rec

    def activate_version(self, capability_id: str, version_str: str) -> CapabilityVersionRecord:
        """Marks a version as active and locks it against future mutations."""
        rec = self.get_version(capability_id, version_str)
        if rec is None:
            raise ValueError(f"Version '{version_str}' not found for capability '{capability_id}'")

        # Deactivate any currently active version
        for v in self.list_versions(capability_id):
            if v.is_active and v.version_id != rec.version_id:
                v.is_active = False

        rec.is_active = True
        rec.activated_at = _now_utc()
        logger.info("Activated capability version: %s v%s", capability_id, version_str)
        return rec

    def get_version(self, capability_id: str, version_str: str) -> Optional[CapabilityVersionRecord]:
        for v in self._versions.get(capability_id, []):
            if v.version_str == version_str:
                return v
        return None

    def get_active_version(self, capability_id: str) -> Optional[CapabilityVersionRecord]:
        for v in self._versions.get(capability_id, []):
            if v.is_active:
                return v
        return None

    def list_versions(self, capability_id: str) -> List[CapabilityVersionRecord]:
        return list(self._versions.get(capability_id, []))


_global_version_manager: Optional[CapabilityVersionManager] = None


def get_capability_version_manager() -> CapabilityVersionManager:
    global _global_version_manager
    if _global_version_manager is None:
        _global_version_manager = CapabilityVersionManager()
    return _global_version_manager
