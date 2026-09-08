"""Proactive detector determining whether incoming events represent useful candidate insights."""

import logging
from typing import Any

from app.proactive.evaluator import InsightEvaluator
from app.proactive.prioritizer import InsightPrioritizer
from app.proactive.safety import ProactiveSafetyGuard
from app.proactive.schemas import CandidateInsight
from app.proactive.state import SourceType

logger = logging.getLogger("kairo.proactive.detector")

# Event names and categories that are considered candidates for proactive intelligence
INTERESTING_CATEGORIES = {
    "workflow.failed",
    "workflow.completed",
    "workflow.approval_required",
    "approval.required",
    "approval.expired",
    "approval.waiting_too_long",
    "github.ci.failed",
    "github.check.failed",
    "github.uncommitted_changes",
    "web_monitor.changed",
    "security.emergency_stop",
    "security.policy_denied",
    "system.recovered",
    "system.error",
}

# Noisy or routine event patterns to explicitly discard
IGNORED_PATTERNS = {
    "tool_read",
    "memory_retrieval",
    "health_check",
    "ping",
    "session_heartbeat",
    "chat_chunk",
}


class ProactiveDetector:
    """Evaluates raw events to decide if they warrant proactive notification and packages candidate insights."""

    @classmethod
    def is_candidate_event(
        cls,
        source_type: str,
        category: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Deterministically determine if an event is useful to surface to the user."""
        cat = category.lower().strip()
        st = source_type.upper().strip()

        # Reject explicitly ignored routine event patterns
        if any(ignored in cat for ignored in IGNORED_PATTERNS):
            return False

        # Reject read-only tool calls
        if payload and payload.get("permission_level") == "READ" and "tool" in cat:
            return False

        # Match known interesting event categories
        if cat in INTERESTING_CATEGORIES:
            return True

        # Match heuristics based on category name
        if any(term in cat for term in ("fail", "error", "expired", "approval", "emergency", "changed")):
            return True

        # Informational workflow completions are candidates (can be filtered by user preferences later)
        if "completed" in cat and st in (SourceType.WORKFLOW, "WORKFLOW"):
            return True

        return False

    @classmethod
    def create_candidate(
        cls,
        user_id: str,
        source_type: SourceType | str,
        category: str,
        payload: dict[str, Any] | None = None,
        source_id: str | None = None,
        chain_depth: int = 0,
    ) -> CandidateInsight | None:
        """Transform an event into a CandidateInsight if it meets candidate criteria."""
        payload = payload or {}

        # 1. Safety check: prevent runaway loops
        ProactiveSafetyGuard.check_chain_depth(chain_depth)

        # 2. Check if event is potentially useful
        if not cls.is_candidate_event(str(source_type), category, payload):
            logger.debug(
                "Event ignored by ProactiveDetector: source=%s category=%s",
                source_type,
                category,
            )
            return None

        # 3. Sanitize payload
        clean_meta = ProactiveSafetyGuard.sanitize_event_payload(payload)

        # 4. Generate deterministic title, summary, action
        title, summary, suggested_action = InsightEvaluator.evaluate_deterministic(
            source_type=source_type,
            category=category,
            metadata=clean_meta,
        )

        # 5. Deterministic priority and actionability calculation
        priority, actionability = InsightPrioritizer.calculate(
            source_type=source_type,
            category=category,
            metadata=clean_meta,
        )

        # Extract state tracking values for cooldown if present
        state_key = clean_meta.get("state_key") or category
        state_value = clean_meta.get("state_value") or clean_meta.get("status")

        # Action payload contains links to resources (workflow, run, PR, approval, monitor)
        action_payload: dict[str, Any] = {
            "source_type": str(source_type),
            "source_id": source_id,
            "category": category,
            "workflow_id": clean_meta.get("workflow_id"),
            "run_id": clean_meta.get("run_id"),
            "approval_id": clean_meta.get("approval_id"),
            "repo": clean_meta.get("repo"),
            "url": clean_meta.get("url"),
            "suggested_action": suggested_action,
        }

        return CandidateInsight(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            category=category,
            title=title,
            summary=summary,
            priority=priority,
            actionability=actionability,
            action_payload=action_payload,
            suggested_action=suggested_action,
            chain_depth=chain_depth,
            state_key=state_key,
            state_value=str(state_value) if state_value is not None else None,
            expires_at=None,
        )
