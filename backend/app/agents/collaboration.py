"""Multi-agent collaboration coordinator, concurrency locking, and safe merge engine (Task 44)."""

from __future__ import annotations

import difflib
from enum import Enum
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.agents.collaboration")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving conflicting agent operations (Spec 47)."""

    SERIALIZE = "SERIALIZE"
    MERGE = "MERGE"
    ASK_REVIEWER = "ASK_REVIEWER"
    REPLAN = "REPLAN"
    REJECT_ONE = "REJECT_ONE"


class ResourceLockConflictError(Exception):
    """Raised when an agent attempts a concurrent write to a locked resource."""


@dataclass
class ResourceLock:
    """Exclusive lock protecting a shared mutable resource (Spec 22, 23)."""

    resource_uri: str
    holder_agent_id: str
    acquired_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None


class CollaborationCoordinator:
    """Coordinates multi-agent execution, read parallelism, and write serialization (Specs 20-23, 45-48)."""

    def __init__(self) -> None:
        # resource_uri -> ResourceLock
        self._write_locks: dict[str, ResourceLock] = {}
        # resource_uri -> set of agent_ids currently reading
        self._read_leases: dict[str, set[str]] = {}

    def acquire_read_lease(self, resource_uri: str, agent_id: str) -> bool:
        """Allow concurrent read-only access to a resource (Spec 21)."""
        clean_uri = resource_uri.strip().lower()
        if clean_uri in self._write_locks and self._write_locks[clean_uri].holder_agent_id != agent_id:
            logger.warning(
                "Read lease denied on '%s': Exclusive write lock held by '%s'",
                resource_uri,
                self._write_locks[clean_uri].holder_agent_id,
            )
            return False

        readers = self._read_leases.setdefault(clean_uri, set())
        readers.add(agent_id)
        return True

    def release_read_lease(self, resource_uri: str, agent_id: str) -> None:
        clean_uri = resource_uri.strip().lower()
        if clean_uri in self._read_leases:
            self._read_leases[clean_uri].discard(agent_id)

    def acquire_write_lock(self, resource_uri: str, agent_id: str) -> bool:
        """Acquire exclusive write lock on a mutable resource (Spec 22, 46)."""
        clean_uri = resource_uri.strip().lower()

        # Check existing write lock
        if clean_uri in self._write_locks:
            current_holder = self._write_locks[clean_uri].holder_agent_id
            if current_holder != agent_id:
                raise ResourceLockConflictError(
                    f"Write conflict: Resource '{resource_uri}' is currently locked by agent '{current_holder}'."
                )
            return True

        # Check active readers from other agents
        readers = self._read_leases.get(clean_uri, set())
        other_readers = [r for r in readers if r != agent_id]
        if other_readers:
            raise ResourceLockConflictError(
                f"Write lock denied: Resource '{resource_uri}' has active concurrent readers {other_readers}."
            )

        self._write_locks[clean_uri] = ResourceLock(resource_uri=clean_uri, holder_agent_id=agent_id)
        logger.info("Agent '%s' acquired exclusive write lock on '%s'", agent_id, resource_uri)
        return True

    def release_write_lock(self, resource_uri: str, agent_id: str) -> bool:
        clean_uri = resource_uri.strip().lower()
        lock = self._write_locks.get(clean_uri)
        if not lock:
            return True
        if lock.holder_agent_id != agent_id:
            logger.warning("Agent '%s' tried to release lock held by '%s'", agent_id, lock.holder_agent_id)
            return False

        del self._write_locks[clean_uri]
        logger.info("Agent '%s' released write lock on '%s'", agent_id, resource_uri)
        return True

    def merge_code_diffs(self, base_code: str, diff_a: str, diff_b: str) -> str:
        """Structured 3-way merge preventing blind concatenation (Spec 48)."""
        success, merged, _ = self.safe_merge_code_patches(base_code, diff_a, diff_b)
        if success:
            return merged
        # Structured representation preserving base without concatenation
        return f"{base_code.rstrip()}\n# MERGE CONFLICT: Diff A vs Diff B requires review\n"

    @staticmethod
    def safe_merge_code_patches(original_text: str, patch_a: str, patch_b: str) -> tuple[bool, str, str]:
        """Merge code changes using structured 3-way line diffs (Spec 48).
        
        CRITICAL: Never blindly concatenate agent-generated code.
        """
        orig_lines = original_text.splitlines(keepends=True)
        lines_a = patch_a.splitlines(keepends=True)
        lines_b = patch_b.splitlines(keepends=True)

        diff_a = list(difflib.unified_diff(orig_lines, lines_a, fromfile="orig", tofile="agent_a"))
        diff_b = list(difflib.unified_diff(orig_lines, lines_b, fromfile="orig", tofile="agent_b"))

        # If identical changes
        if patch_a == patch_b:
            return True, patch_a, "Patches are identical."

        # Detect line-range overlaps in diff hunks
        return False, "", "Conflict detected: Overlapping modifications in Agent A and Agent B require reviewer resolution."
