"""Priority resolution and priority integrity enforcement for Kairo Notifications (Task 34, Spec 5, 6, 7)."""

import logging
from typing import Any

from app.notifications.schemas import NotificationPriority, NotificationType

logger = logging.getLogger("kairo.notifications.priority")


class PriorityResolver:
    """
    Authoritative priority assignment engine.
    Guarantees Priority Integrity: Model-generated text or claims cannot override system policy.
    """

    # Baseline rules mapping event namespaces and categories to authoritative priorities
    POLICY_MAP: dict[str, NotificationPriority] = {
        # Security events
        "security.policy_violation": NotificationPriority.URGENT,
        "security.emergency_stop": NotificationPriority.URGENT,
        "security.revocation": NotificationPriority.HIGH,
        "device.revoked": NotificationPriority.HIGH,
        "session.all_revoked": NotificationPriority.HIGH,
        # Approvals
        "approval.requested": NotificationPriority.HIGH,
        "task.waiting_approval": NotificationPriority.HIGH,
        # Task lifecycle
        "task.failed": NotificationPriority.HIGH,
        "task.completed": NotificationPriority.NORMAL,
        "task.waiting_user": NotificationPriority.HIGH,
        "task.step.failed": NotificationPriority.NORMAL,
        "task.started": NotificationPriority.LOW,
        # Automation / CI / Deployments
        "github.ci.failed": NotificationPriority.NORMAL,
        "workflow.failed": NotificationPriority.HIGH,
        "workflow.completed": NotificationPriority.NORMAL,
        # System & Health
        "system.outage": NotificationPriority.HIGH,
        "system.degradation": NotificationPriority.NORMAL,
        "system.recovered": NotificationPriority.LOW,
        # Research & Proactive
        "research.completed": NotificationPriority.LOW,
        "insight.detected": NotificationPriority.LOW,
    }

    @classmethod
    def resolve_priority(
        cls,
        event_type: str,
        notification_type: NotificationType,
        payload: dict[str, Any] | None = None,
        suggested_priority: NotificationPriority | str | None = None,
    ) -> NotificationPriority:
        """
        Determine canonical notification priority based on strict system policy.
        Ignores adversarial or hallucinated 'URGENT' claims from untrusted model outputs.
        """
        payload = payload or {}

        # 1. Exact match in policy map
        if event_type in cls.POLICY_MAP:
            base_priority = cls.POLICY_MAP[event_type]
        else:
            # 2. Namespace fallback
            prefix = event_type.split(".")[0] if "." in event_type else event_type
            if prefix == "security":
                base_priority = NotificationPriority.HIGH
            elif prefix == "approval":
                base_priority = NotificationPriority.HIGH
            elif prefix in ("task", "workflow", "github"):
                base_priority = NotificationPriority.NORMAL
            else:
                base_priority = NotificationPriority.LOW

        # 3. Payload-driven risk escalation (from trusted security center metadata)
        risk_level = str(payload.get("risk_level", "")).upper()
        if risk_level == "CRITICAL" or payload.get("critical") is True:
            base_priority = NotificationPriority.URGENT
        elif risk_level == "HIGH" and base_priority in (NotificationPriority.LOW, NotificationPriority.NORMAL):
            base_priority = NotificationPriority.HIGH

        # 4. Approvals are strictly at least HIGH
        if notification_type == NotificationType.APPROVAL and base_priority in (NotificationPriority.LOW, NotificationPriority.NORMAL):
            base_priority = NotificationPriority.HIGH

        # 5. Priority Integrity check against suggested_priority
        # Model output cannot escalate above policy determination
        if suggested_priority:
            try:
                sug = NotificationPriority(suggested_priority) if isinstance(suggested_priority, str) else suggested_priority
                if sug == NotificationPriority.URGENT and base_priority not in (NotificationPriority.HIGH, NotificationPriority.URGENT):
                    logger.warning(
                        "Priority Integrity Enforced: Model claimed URGENT for '%s', system policy constrained to '%s'.",
                        event_type,
                        base_priority.value,
                    )
                # Model may lower its own priority (e.g. routine report to LOW), but cannot bypass policy minimums
                elif sug.value < base_priority.value and notification_type != NotificationType.APPROVAL:
                    # Allow de-escalation for non-approval non-security
                    if notification_type not in (NotificationType.SECURITY, NotificationType.APPROVAL):
                        base_priority = sug
            except ValueError:
                pass

        return base_priority
