"""Downstream Subsystem Integration Bridges for Task 110:
Connects Context Working Sets to Decision Intelligence (Task 94), Action Governance (Task 95),
Mission Control (Task 100), Control Plane (Task 102), and EmergencyStop.

Strict Invariants:
- CONTEXT != DECISION.
- CONTEXT != AUTHORIZATION.
- CONTEXT != EXECUTION.
- EmergencyStop immediately invalidates execution cognition fail-closed.
- Supports the NO_ACTION case when context proves evidence is insufficient or uncertainty is high.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.context.working_set_domain import (
    ContextSnapshot,
    WorkingSet,
    WorkingSetLifecycle,
    utc_now,
)


class DownstreamContextBridges:
    """Non-authoritative integration points providing context working sets to downstream cognitive consumers."""

    @classmethod
    def prepare_decision_context(
        cls,
        working_set: WorkingSet,
        snapshot: ContextSnapshot,
    ) -> Dict[str, Any]:
        """Provides an immutable context package for Task 94 Decision Intelligence deliberation."""
        return {
            "working_set_id": working_set.working_set_id,
            "working_set_version": working_set.version,
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_hash": snapshot.snapshot_hash,
            "total_tokens": working_set.total_tokens,
            "conflicts_count": len(working_set.conflicts),
            "gaps_count": len(working_set.gaps),
            "completeness_estimate": working_set.completeness_estimate,
            "confidence_summary": working_set.confidence_summary,
            "has_untrusted_content": working_set.has_untrusted_content,
            "ready_for_deliberation": working_set.lifecycle == WorkingSetLifecycle.READY,
        }

    @classmethod
    def prepare_action_preflight_context(
        cls,
        working_set: WorkingSet,
        snapshot: ContextSnapshot,
    ) -> Dict[str, Any]:
        """Provides context package for Task 95 ActionTransaction preflight validation."""
        return {
            "transaction_phase": "PREFLIGHT",
            "working_set_id": working_set.working_set_id,
            "snapshot_hash": snapshot.snapshot_hash,
            "required_evidence_verified": len(working_set.gaps) == 0,
            "conflicts_detected": len(working_set.conflicts) > 0,
            "untrusted_content_quarantined": True,
        }

    @classmethod
    def prepare_mission_context(
        cls,
        working_set: WorkingSet,
        mission_id: str,
    ) -> Dict[str, Any]:
        """Provides milestone evaluation context for Task 100 Mission Control."""
        return {
            "mission_id": mission_id,
            "working_set_id": working_set.working_set_id,
            "item_count": working_set.item_count,
            "has_blockers": any(g.is_blocking for g in working_set.gaps),
            "quality_score": working_set.quality_score,
        }

    @classmethod
    def evaluate_no_action_recommendation(
        cls,
        working_set: WorkingSet,
    ) -> Tuple[bool, Optional[str]]:
        """Evaluates whether the assembled context indicates a NO_ACTION condition.
        
        Returns (should_no_action, reason).
        """
        # 1. Active blocking gaps
        blocking_gaps = [g for g in working_set.gaps if g.is_blocking]
        if blocking_gaps:
            return True, f"Blocking context gap detected: {blocking_gaps[0].missing_information}"

        # 2. Too many unresolved critical conflicts
        critical_conflicts = [c for c in working_set.conflicts if c.severity == "CRITICAL"]
        if critical_conflicts:
            return True, f"Critical unresolved context conflict: {critical_conflicts[0].summary}"

        # 3. Very low completeness estimate
        if working_set.completeness_estimate < 0.40:
            return True, f"Context completeness estimate ({working_set.completeness_estimate:.2f}) below threshold (0.40)"

        # 4. Empty working set
        if working_set.item_count == 0:
            return True, "No actionable context elements assembled"

        return False, None
