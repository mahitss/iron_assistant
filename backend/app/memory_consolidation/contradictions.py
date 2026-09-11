"""Contradiction detection and temporal contextualization engine for Task 68.

Enforces:
- Spec 12: Contradiction engine with explicit contextualization
- Invariant: Never silently overwrite memories; preserve competing claims and mark uncertainty
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime

from app.memory_consolidation.schemas import (
    ConflictResolutionType,
    ContradictionReport,
    ContradictionStatus,
    DurableMemory,
    MemoryLifecycleState,
)

logger = logging.getLogger("kairo.memory_consolidation.contradictions")

OPPOSING_ASSERTION_PAIRS = [
    ("enabled", "disabled"),
    ("online", "offline"),
    ("active", "inactive"),
    ("production", "staging"),
    ("port 8080", "port 9090"),
    ("port 80", "port 443"),
    ("requires auth", "no auth required"),
    ("deprecated", "supported"),
    ("read only", "read write"),
]


class ContradictionEngine:
    """Detects and contextualizes conflicting memory assertions (Spec 12)."""

    @classmethod
    def are_statements_conflicting(cls, text_a: str, text_b: str) -> tuple[bool, str]:
        """Check if two memory contents contain contradictory assertions."""
        sa = text_a.lower()
        sb = text_b.lower()

        # Check opposing keyword pairs
        for pos, neg in OPPOSING_ASSERTION_PAIRS:
            if (pos in sa and neg in sb) or (neg in sa and pos in sb):
                return True, f"DIRECT_OPPOSING_ASSERTIONS: '{pos}' vs '{neg}'"

        # Check numeric property discrepancies (e.g. version = 14 vs version = 15)
        pattern_kv = re.compile(r"(\w+)\s*(?:=|is|runs on|version|port)\s*[:=]?\s*(\w+)")
        matches_a = dict(pattern_kv.findall(sa))
        matches_b = dict(pattern_kv.findall(sb))
        for k in matches_a:
            if k in matches_b and matches_a[k] != matches_b[k]:
                return (
                    True,
                    f"INCOMPATIBLE_PROPERTY_VALUE: property '{k}' has '{matches_a[k]}' vs '{matches_b[k]}'",
                )

        # Check numeric count discrepancies (e.g., "0 errors" vs "12 errors")
        pattern_num = re.compile(r"(\d+)\s+([a-zA-Z]+)")
        nums_a = {unit: int(val) for val, unit in pattern_num.findall(sa)}
        nums_b = {unit: int(val) for val, unit in pattern_num.findall(sb)}
        for unit in nums_a:
            if unit in nums_b and nums_a[unit] != nums_b[unit]:
                return True, f"NUMERIC_DISCREPANCY: '{nums_a[unit]} {unit}' vs '{nums_b[unit]} {unit}'"

        return False, "NO_CONTRADICTION"

    @classmethod
    def analyze_conflict(cls, mem_a: DurableMemory, mem_b: DurableMemory) -> ContradictionReport | None:
        """Analyze potential conflict between two memories, determining if contextualized or conflicting."""
        is_conflicting, reason = cls.are_statements_conflicting(mem_a.content, mem_b.content)
        if not is_conflicting:
            return None

        conflict_id = f"cnf_{uuid.uuid4().hex[:10]}"
        now = datetime.now(UTC)

        # 1. Check if different environments contextualize the claims
        env_a = mem_a.structured_payload.get("environment", "unknown")
        env_b = mem_b.structured_payload.get("environment", "unknown")
        if env_a != env_b and env_a != "unknown" and env_b != "unknown":
            return ContradictionReport(
                conflict_id=conflict_id,
                memory_a_id=mem_a.memory_id,
                memory_b_id=mem_b.memory_id,
                status=ContradictionStatus.CONTEXTUALIZED,
                explanation=f"Contextual divergence: applies to different environments ({env_a} vs {env_b}).",
                environment_context={"env_a": env_a, "env_b": env_b},
                resolution_type=ConflictResolutionType.ENVIRONMENT_BASED,
                tenant_id=mem_a.tenant_id,
            )

        # 2. Check if one is temporally newer and explicitly supersedes the earlier observation
        time_diff = (mem_b.observed_at - mem_a.observed_at).total_seconds()
        if abs(time_diff) > 3600:  # More than 1 hour apart
            newer, older = (mem_b, mem_a) if time_diff > 0 else (mem_a, mem_b)
            # If newer has higher or equal confidence
            if newer.confidence >= older.confidence:
                return ContradictionReport(
                    conflict_id=conflict_id,
                    memory_a_id=older.memory_id,
                    memory_b_id=newer.memory_id,
                    status=ContradictionStatus.SUPERSEDED,
                    explanation=f"Temporal supersession: {newer.memory_id} observed later with fresh evidence.",
                    temporal_context={
                        "older_observed_at": older.observed_at.isoformat(),
                        "newer_observed_at": newer.observed_at.isoformat(),
                    },
                    resolution_type=ConflictResolutionType.TIME_BASED,
                    tenant_id=mem_a.tenant_id,
                )

        # 3. Otherwise, genuine unresolved contradiction
        mem_a.status = MemoryLifecycleState.CONFLICTED
        mem_b.status = MemoryLifecycleState.CONFLICTED

        return ContradictionReport(
            conflict_id=conflict_id,
            memory_a_id=mem_a.memory_id,
            memory_b_id=mem_b.memory_id,
            status=ContradictionStatus.CONFLICTED,
            explanation=f"Unresolved contradiction: {reason}. Both claims preserved; uncertainty surfaced during retrieval.",
            temporal_context={"detected_at": now.isoformat()},
            tenant_id=mem_a.tenant_id,
        )
