"""Root-cause correlation and causal graph failure linking for Kairo Reliability (Task 88)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from app.reliability.models import FailureRecord
from app.reliability.taxonomy import FailureSeverity, FailureType

logger = logging.getLogger("kairo.reliability.correlator")


# Known topological causal dependency hierarchies (upstream causes downstream)
# E.g., if database fails, workflow storage, tool execution, and user queries fail downstream.
SYSTEM_DEPENDENCY_EDGES: Dict[str, List[str]] = {
    "database": ["workflow", "memory", "auth", "tasks"],
    "native_runtime": ["native_tool", "sandbox", "computer", "network_fabric"],
    "network_fabric": ["web_research", "http_fetch", "external_api"],
    "redis": ["coordination", "realtime_cache", "locks"],
    "sandbox": ["governed_execution", "tool_runner"],
    "security_center": ["approval_registry", "governance"],
}


class RootCauseCorrelator:
    """Correlates multiple failure events into causal trees and identifies root-cause candidates."""

    def __init__(self) -> None:
        # In-memory graph of causal links: child_failure_id -> parent_failure_id
        self._causal_parents: Dict[str, str] = {}
        # Correlation index: correlation_id -> List[failure_id]
        self._correlation_index: Dict[str, List[str]] = {}
        # Trace index: trace_id -> List[failure_id]
        self._trace_index: Dict[str, List[str]] = {}

    def correlate(
        self,
        new_failure: FailureRecord,
        active_failures: List[FailureRecord],
    ) -> str:
        """Determines the most plausible root cause for a new failure.

        1. Direct Causation: If new_failure has causation_id matching a known failure,
           that failure's root cause is inherited.
        2. Distributed Trace Correlation: If another failure shares trace_id,
           topological ancestor is selected.
        3. Topological Subsystem Precedence: Upstream components (DB, Rust daemon)
           take precedence over downstream victims (workflows, tools).
        4. Temporal Precedence: Earlier failures in the same correlation context
           are preferred.
        """
        # Index the failure
        if new_failure.correlation_id and new_failure.correlation_id != "unspecified":
            self._correlation_index.setdefault(new_failure.correlation_id, []).append(new_failure.failure_id)
        if new_failure.trace_id:
            self._trace_index.setdefault(new_failure.trace_id, []).append(new_failure.failure_id)

        # 1. Direct Causation match
        if new_failure.causation_id:
            for f in active_failures:
                if f.failure_id == new_failure.causation_id:
                    self._causal_parents[new_failure.failure_id] = f.failure_id
                    logger.debug(
                        "Direct causation linked: %s -> %s (root: %s)",
                        new_failure.failure_id,
                        f.failure_id,
                        f.root_cause_candidate,
                    )
                    return f.root_cause_candidate

        # 2. Trace Context & Component Hierarchy match
        candidates = [
            f for f in active_failures
            if f.failure_id != new_failure.failure_id and (
                (f.correlation_id == new_failure.correlation_id and f.correlation_id != "unspecified")
                or (f.trace_id and f.trace_id == new_failure.trace_id)
            )
        ]

        if not candidates:
            # Standalone failure
            return new_failure.component

        # Look for topological upstream culprit among candidates
        for candidate in candidates:
            downstreams = SYSTEM_DEPENDENCY_EDGES.get(candidate.component.lower(), [])
            if new_failure.component.lower() in downstreams:
                self._causal_parents[new_failure.failure_id] = candidate.failure_id
                logger.info(
                    "Topological causal dependency detected: %s (%s) caused downstream %s (%s)",
                    candidate.component,
                    candidate.failure_id,
                    new_failure.component,
                    new_failure.failure_id,
                )
                return candidate.root_cause_candidate

        # Fallback to temporal precedence (earliest failure with highest severity)
        sorted_candidates = sorted(
            candidates,
            key=lambda c: (c.severity.rank, c.timestamp),
        )
        primary_candidate = sorted_candidates[0]
        self._causal_parents[new_failure.failure_id] = primary_candidate.failure_id
        return primary_candidate.root_cause_candidate

    def get_causal_chain(self, failure_id: str) -> List[str]:
        """Traverse upwards to reconstruct the chain of parent failure IDs."""
        chain = [failure_id]
        curr = failure_id
        visited: Set[str] = {failure_id}
        while curr in self._causal_parents:
            parent = self._causal_parents[curr]
            if parent in visited:
                break
            visited.add(parent)
            chain.append(parent)
            curr = parent
        return chain
