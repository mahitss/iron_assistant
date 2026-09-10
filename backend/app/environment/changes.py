"""Change Detection, Classification, and Causal Evidence Validation (Task 54, Prompts #59-#65)."""

from __future__ import annotations

import uuid
from typing import Any

from app.environment.schemas import ChangeSignificance, ChangeType, EnvironmentChange
from app.environment.temporal import utc_now


class ChangeDetector:
    """Detects mutations, determines significance, and enforces evidence-based causality."""

    @staticmethod
    def create_change_record(
        resource_id: str,
        change_type: ChangeType,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
        source: str,
        significance: ChangeSignificance | None = None,
        confidence: float = 1.0,
        verification: dict[str, Any] | None = None,
    ) -> EnvironmentChange:
        # Determine significance if not specified
        if significance is None:
            if change_type in (ChangeType.FAILED, ChangeType.REDEPLOYED):
                significance = ChangeSignificance.HIGH
            elif change_type in (ChangeType.CREATED, ChangeType.REMOVED):
                significance = ChangeSignificance.MEDIUM
            elif change_type == ChangeType.SCALED:
                significance = ChangeSignificance.LOW
            else:
                significance = ChangeSignificance.LOW

        cid = f"chg_{uuid.uuid4().hex[:10]}"
        return EnvironmentChange(
            change_id=cid,
            resource=resource_id,
            change_type=change_type,
            before=before,
            after=after,
            timestamp=utc_now(),
            source=source,
            significance=significance,
            confidence=confidence,
            verification=verification or {"verified": False},
        )

    @staticmethod
    def correlate_changes(changes: list[EnvironmentChange], window_seconds: int = 300) -> list[list[EnvironmentChange]]:
        """Groups changes occurring across interdependent resources within the same time window."""
        if not changes:
            return []
        sorted_changes = sorted(changes, key=lambda c: c.timestamp)
        clusters: list[list[EnvironmentChange]] = []
        current_cluster: list[EnvironmentChange] = [sorted_changes[0]]

        for c in sorted_changes[1:]:
            prev_ts = current_cluster[-1].timestamp
            if (c.timestamp - prev_ts).total_seconds() <= window_seconds:
                current_cluster.append(c)
            else:
                clusters.append(current_cluster)
                current_cluster = [c]
        if current_cluster:
            clusters.append(current_cluster)
        return clusters

    @staticmethod
    def validate_causal_claim(
        candidate_change: EnvironmentChange,
        incident_id: str,
        incident_time: Any,
        causal_evidence: dict[str, Any] | None,
    ) -> bool:
        """Prompt #64, #65: Do not claim a change caused an incident solely because it happened first. Require evidence."""
        if not causal_evidence:
            return False
        # Must have log trace, error stack pointing to change, or explicit dependency path
        has_trace = "trace_id" in causal_evidence or "stack_trace" in causal_evidence
        has_explicit_link = causal_evidence.get("direct_causality_verified") is True
        return has_trace or has_explicit_link
