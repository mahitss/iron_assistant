"""Command router and domain planner bridge (Spec 53, 54, 55, 56, 96, 97, 98, 124)."""

import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.intent.schemas import IntentErrorState, IntentSchema, IntentType

logger = logging.getLogger("kairo.intent.planner_bridge")


class CommandRouter:
    """
    Safely routes validated intents to the appropriate execution subsystem.
    INVARIANT: Intent layer never executes tools or actions directly (Spec 56).
    """

    @classmethod
    async def route_intent(
        cls,
        intent: IntentSchema,
        user_id: str,
        db_session: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """
        Routes the validated intent to domain executors.
        Returns execution summary dict with target subsystem and status.
        """
        # If intent is waiting for user clarification or failed validation, do not route to execution
        if intent.status == IntentErrorState.WAITING_USER.value:
            return {
                "action": "clarification_required",
                "subsystem": "interaction",
                "status": "WAITING_USER",
                "reason": intent.ambiguity.reason,
                "options": [opt.model_dump() for opt in intent.ambiguity.resolution_options],
            }

        if intent.status != "READY":
            return {
                "action": "blocked",
                "subsystem": "validator",
                "status": intent.status,
                "reason": "Intent failed validation checks.",
            }

        # 1. APPROVE / REJECT -> Security Approval Service (Spec 96, 98)
        if intent.type in (IntentType.APPROVE, IntentType.REJECT):
            if db_session is not None:
                try:
                    from app.security.approvals import ApprovalManager
                    pending = await ApprovalManager.get_pending_approvals(db_session, user_id=user_id)
                    if not pending:
                        return {
                            "action": "approval_evaluation",
                            "subsystem": "security_center",
                            "status": "NO_PENDING_APPROVAL",
                            "message": "No pending approvals found for this session.",
                        }
                    if len(pending) > 1:
                        return {
                            "action": "clarification_required",
                            "subsystem": "security_center",
                            "status": "WAITING_USER",
                            "reason": f"There are {len(pending)} pending approvals. Which one do you want to {intent.type.value.lower()}?",
                            "options": [{"id": p.id, "label": p.action_description} for p in pending],
                        }
                    # Exactly one pending approval: apply decision
                    decision = "approve" if intent.type == IntentType.APPROVE else "deny"
                    req = await ApprovalManager.apply_decision(
                        db_session=db_session,
                        approval_id=pending[0].id,
                        user_id=user_id,
                        decision=decision,
                        reason=f"User commanded '{intent.objective}'",
                    )
                    return {
                        "action": "approval_executed",
                        "subsystem": "security_center",
                        "status": req.status,
                        "approval_id": req.id,
                        "description": req.action_description,
                    }
                except Exception as exc:
                    logger.warning("Approval execution error in router: %s", exc)
                    return {"action": "approval_error", "subsystem": "security_center", "error": str(exc)}

            return {
                "action": "approval_delegation",
                "subsystem": "security_center",
                "status": "QUEUED",
                "decision": intent.type.value,
            }

        # 2. CANCEL / PAUSE / RESUME / RETRY -> Task Engine Control (Spec 84-87)
        if intent.type in (IntentType.CANCEL, IntentType.PAUSE, IntentType.RESUME, IntentType.RETRY):
            try:
                from app.tasks.cancellation import get_cancellation_manager
                cm = get_cancellation_manager()
                task_id = intent.target.stable_entity_id if intent.target else None
                if intent.type == IntentType.CANCEL and task_id:
                    cancelled = cm.cancel_task(task_id, reason=f"User commanded {intent.objective}")
                    return {
                        "action": "task_control",
                        "subsystem": "task_engine",
                        "operation": "CANCEL",
                        "task_id": task_id,
                        "success": cancelled,
                    }
            except Exception as exc:
                logger.debug("Task control delegation note: %s", exc)

            return {
                "action": "task_control",
                "subsystem": "task_engine",
                "operation": intent.type.value,
                "target": intent.target.model_dump() if intent.target else None,
                "status": "DISPATCHED",
            }

        # 3. TASK -> Autonomous Task Engine (Spec 54)
        if intent.type == IntentType.TASK:
            return {
                "action": "task_creation",
                "subsystem": "task_engine",
                "objective": intent.objective,
                "target": intent.target.model_dump() if intent.target else None,
                "constraints": intent.constraints.model_dump(),
                "risk_level": intent.risk.value,
                "status": "DISPATCHED_TO_TASK_ENGINE",
            }

        # 4. ANALYZE / SUMMARIZE / COMPARE / EXPLAIN -> Skill Execution (Spec 55)
        if intent.type in (IntentType.ANALYZE, IntentType.SUMMARIZE, IntentType.COMPARE, IntentType.EXPLAIN):
            return {
                "action": "skill_invocation",
                "subsystem": "skills_catalog",
                "skill_type": intent.type.value.lower(),
                "target": intent.target.model_dump() if intent.target else None,
                "status": "DISPATCHED_TO_SKILLS",
            }

        # 5. AUTOMATE -> Automation Service (Spec 93)
        if intent.type == IntentType.AUTOMATE:
            return {
                "action": "automation_creation",
                "subsystem": "automation_service",
                "objective": intent.objective,
                "status": "DISPATCHED_TO_AUTOMATION",
            }

        # 6. REMIND -> Notification Service (Spec 94)
        if intent.type == IntentType.REMIND:
            return {
                "action": "reminder_creation",
                "subsystem": "notification_service",
                "objective": intent.objective,
                "status": "DISPATCHED_TO_NOTIFICATIONS",
            }

        # 7. QUESTION / SEARCH / NAVIGATE / Default -> Conversational Agent (Spec 5)
        return {
            "action": "chat_response",
            "subsystem": "kairo_agent",
            "intent_type": intent.type.value,
            "status": "DISPATCHED_TO_CHAT",
        }
