"""Decision Provenance and Event Dispatcher for Kairo Governance Engine (Task 36).

Ensures:
- Every meaningful policy decision is recorded and traceable by evaluation_id.
- Sensitive credentials/tokens are never persisted in provenance logs.
- Event Bus notifications are published for audit and reactive subsystems.
"""

from collections import OrderedDict
from datetime import UTC, datetime
import logging
from typing import Any

from app.events.bus import EventBus, get_event_bus
from app.events.schemas import Event
from app.policy.schemas import PolicyContext, PolicyDecision, PolicyDecisionType

logger = logging.getLogger("kairo.policy.decisions")


class DecisionProvenanceManager:
    """Manages policy decision persistence, query by evaluation_id, and event broadcasting."""

    def __init__(self, max_in_memory: int = 1000) -> None:
        self._evaluations: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_in_memory = max_in_memory

    def record_evaluation(self, context: PolicyContext, decision: PolicyDecision) -> None:
        """Store decision provenance record in sanitized memory buffer."""
        clean_target = self._sanitize_target(context.target)

        record = {
            "evaluation_id": decision.evaluation_id,
            "policy_id": decision.policy_id,
            "policy_version": decision.policy_version,
            "user_id": (context.user or {}).get("id") or (context.user or {}).get("user_id"),
            "session_id": (context.session or {}).get("id"),
            "project_id": (context.project or {}).get("id"),
            "environment": context.environment,
            "action": context.action,
            "target": clean_target,
            "tool_name": context.tool.get("name") if isinstance(context.tool, dict) else context.tool,
            "risk_level": decision.risk_level.value,
            "decision": decision.decision.value,
            "reason_code": decision.reason_code,
            "safe_explanation": decision.safe_explanation,
            "constraints": decision.constraints,
            "required_approval": decision.required_approval,
            "required_authentication": decision.required_authentication,
            "allowed_scope": decision.allowed_scope,
            "matched_policies": decision.matched_policies,
            "is_simulated": decision.simulated,
            "timestamp": decision.timestamp.isoformat(),
            "expires_at": decision.expires_at.isoformat() if decision.expires_at else None,
        }

        self._evaluations[decision.evaluation_id] = record
        if len(self._evaluations) > self._max_in_memory:
            self._evaluations.popitem(last=False)

    def get_evaluation(self, evaluation_id: str) -> dict[str, Any] | None:
        """Retrieve evaluation provenance record by its ID."""
        return self._evaluations.get(evaluation_id)

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent policy evaluation records."""
        records = list(self._evaluations.values())
        records.reverse()
        return records[:limit]

    async def emit_decision_events(self, context: PolicyContext, decision: PolicyDecision) -> None:
        """Publish events to the unified event bus (Section 103)."""
        if decision.simulated:
            return  # Do not fire system-wide events for simulations

        bus: EventBus = get_event_bus()
        now = datetime.now(UTC)
        user_id = (context.user or {}).get("id") or (context.user or {}).get("user_id") or "system"

        base_payload = {
            "evaluation_id": decision.evaluation_id,
            "decision": decision.decision.value,
            "action": context.action,
            "environment": context.environment,
            "risk_level": decision.risk_level.value,
            "reason_code": decision.reason_code,
            "policy_id": decision.policy_id,
        }

        # 1. Emit general policy.evaluated
        try:
            await bus.publish(Event(
                event_type="policy.evaluated",
                source="system",
                user_id=user_id,
                payload=base_payload,
                timestamp=now,
            ))
        except Exception as e:
            logger.debug(f"Could not publish policy.evaluated event: {e}")

        # 2. Emit specific event based on decision outcome
        specific_type: str | None = None
        if decision.decision == PolicyDecisionType.DENY:
            specific_type = "policy.denied"
        elif decision.decision == PolicyDecisionType.REQUIRE_APPROVAL:
            specific_type = "policy.approval_required"
        elif decision.decision == PolicyDecisionType.REQUIRE_CONFIRMATION:
            specific_type = "policy.confirmation_required"
        elif decision.decision == PolicyDecisionType.REQUIRE_STEP_UP_AUTH:
            specific_type = "policy.step_up_required"

        if specific_type:
            try:
                await bus.publish(Event(
                    event_type=specific_type,
                    source="system",
                    user_id=user_id,
                    payload={**base_payload, "safe_explanation": decision.safe_explanation},
                    timestamp=now,
                ))
            except Exception as e:
                logger.debug(f"Could not publish {specific_type} event: {e}")

    @staticmethod
    def _sanitize_target(target: Any) -> str:
        """Sanitize target to prevent logging sensitive payload values."""
        if isinstance(target, dict):
            # Extract safe identifier keys
            for key in ("id", "name", "path", "repository", "endpoint", "environment", "action"):
                if key in target:
                    return f"{key}:{target[key]}"
            return "sanitized_target_dict"
        return str(target)[:120] if target is not None else ""


# Global singleton instance
decision_provenance_manager = DecisionProvenanceManager()
