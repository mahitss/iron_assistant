"""Deterministic priority calculation and actionability classification."""

import logging
from typing import Any

from app.proactive.state import Actionability, InsightPriority, SourceType

logger = logging.getLogger("kairo.proactive.prioritizer")


class InsightPrioritizer:
    """Calculates priority and actionability deterministically based on event types and metadata."""

    @classmethod
    def calculate(
        cls,
        source_type: SourceType | str,
        category: str,
        metadata: dict[str, Any] | None = None,
        llm_suggested_priority: str | None = None,
    ) -> tuple[InsightPriority, Actionability]:
        """Determine priority and actionability.

        SAFETY: Critical priority is strictly application-controlled and cannot be set by LLM alone.
        """
        meta = metadata or {}
        st = str(source_type).upper()
        cat = category.lower()

        # 1. SECURITY & EMERGENCY STOP -> Always CRITICAL
        if st in (SourceType.SECURITY, "SECURITY") or "emergency_stop" in cat:
            return InsightPriority.CRITICAL, Actionability.ACTION_REQUIRED

        # 2. APPROVALS -> Always HIGH / APPROVAL_REQUIRED
        if st in (SourceType.APPROVAL, "APPROVAL") or "approval" in cat:
            return InsightPriority.HIGH, Actionability.APPROVAL_REQUIRED

        # 3. WORKFLOW FAILURES -> HIGH
        if st in (SourceType.WORKFLOW, "WORKFLOW"):
            if "fail" in cat or meta.get("status") == "failed":
                return InsightPriority.HIGH, Actionability.ACTION_REQUIRED
            if "complete" in cat or meta.get("status") == "completed":
                return InsightPriority.LOW, Actionability.INFORMATIONAL

        # 4. GITHUB / CI CHECK FAILURES
        if st in (SourceType.GITHUB, "GITHUB"):
            branch = str(meta.get("branch", "")).lower()
            is_main_or_prod = branch in ("main", "master", "prod", "production") or meta.get("is_prod", False)
            if "fail" in cat or meta.get("conclusion") in ("failure", "timed_out"):
                if is_main_or_prod:
                    return InsightPriority.HIGH, Actionability.ACTION_REQUIRED
                return InsightPriority.MEDIUM, Actionability.ACTION_REQUIRED
            if "uncommitted" in cat:
                return InsightPriority.MEDIUM, Actionability.ACTION_REQUIRED
            return InsightPriority.LOW, Actionability.INFORMATIONAL

        # 5. WEB MONITOR CHANGES -> MEDIUM / INFORMATIONAL
        if st in (SourceType.WEB_MONITOR, "WEB_MONITOR") or "web" in cat:
            return InsightPriority.MEDIUM, Actionability.INFORMATIONAL

        # 6. SYSTEM EVENTS
        if st in (SourceType.SYSTEM, "SYSTEM"):
            if "fail" in cat or "error" in cat:
                return InsightPriority.HIGH, Actionability.ACTION_REQUIRED
            if "recovered" in cat:
                return InsightPriority.MEDIUM, Actionability.INFORMATIONAL
            return InsightPriority.LOW, Actionability.INFORMATIONAL

        # 7. LLM Suggestion fallback (Never allows CRITICAL)
        if llm_suggested_priority:
            p_upper = llm_suggested_priority.upper()
            if p_upper == InsightPriority.HIGH:
                return InsightPriority.HIGH, Actionability.INFORMATIONAL
            if p_upper == InsightPriority.MEDIUM:
                return InsightPriority.MEDIUM, Actionability.INFORMATIONAL
            if p_upper == InsightPriority.LOW:
                return InsightPriority.LOW, Actionability.INFORMATIONAL

        return InsightPriority.MEDIUM, Actionability.INFORMATIONAL

    @classmethod
    def meets_priority_threshold(cls, item_priority: str, min_priority: str) -> bool:
        """Check if an insight meets or exceeds user minimum priority threshold."""
        weights = {
            InsightPriority.LOW: 1,
            InsightPriority.MEDIUM: 2,
            InsightPriority.HIGH: 3,
            InsightPriority.CRITICAL: 4,
        }
        item_weight = weights.get(item_priority.upper(), 2)
        min_weight = weights.get(min_priority.upper(), 1)
        return item_weight >= min_weight
