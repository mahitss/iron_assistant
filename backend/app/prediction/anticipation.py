"""User Need Anticipation, Proactive Suggestions, and Anti-Creepy Privacy Defenses (Task 47)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.prediction.anticipation")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CreepyInferenceError(Exception):
    """Raised when an anticipation attempt tries to infer sensitive personal attributes or behavior (Spec 89, 90)."""


@dataclass
class ProactiveSuggestion:
    """Non-consequential recommendation anticipated from authorized project/task patterns (Spec 88-95).
    
    CRITICAL INVARIANT: Suggestion != Action! (Spec 94)
    Suggestions NEVER execute automatically.
    """

    suggestion_id: str
    context: str
    message: str
    suggestion_text: str = ""
    action_preview: Optional[str] = None
    confidence: float = 0.5
    requires_confirmation: bool = True
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.suggestion_text and self.message:
            self.suggestion_text = self.message
        elif not self.message and self.suggestion_text:
            self.message = self.suggestion_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggestion_id": self.suggestion_id,
            "context": self.context,
            "message": self.message,
            "suggestion_text": self.suggestion_text,
            "action_preview": self.action_preview,
            "confidence": round(self.confidence, 3),
            "requires_confirmation": self.requires_confirmation,
            "created_at": self.created_at.isoformat(),
        }


class UserNeedAnticipator:
    """Predicts authorized workflow needs (e.g. 'CI passed; prepare release draft?') (Spec 88-95)."""

    # Prohibited personal inference keywords (Spec 89, 90, 191)
    FORBIDDEN_SENSITIVE_DOMAINS = {
        "health", "medical", "mood", "political", "relationship",
        "religious", "biometric", "financial_speculation", "personal_health",
    }

    @classmethod
    def anticipate_workflow_step(
        cls,
        current_event: str,
        authorized_task_context: str,
        user_preference_history: Optional[List[str]] = None,
    ) -> Optional[ProactiveSuggestion]:
        """Enforce Spec 88, 93: Suggest workflow actions without automatic execution or creepy inferences."""
        for forbidden in cls.FORBIDDEN_SENSITIVE_DOMAINS:
            if forbidden in current_event.lower() or forbidden in authorized_task_context.lower():
                logger.critical("CREEPY INFERENCE BLOCKED: Attempted prediction on '%s'", forbidden)
                raise CreepyInferenceError(f"Proactive anticipation is strictly prohibited on sensitive domain: {forbidden}")

        sid = f"sug_{uuid.uuid4().hex[:8]}"

        if "ci" in current_event.lower() and "pass" in current_event.lower():
            msg = "CI workflow passed successfully. Would you like to proceed with staging deployment?"
            return ProactiveSuggestion(
                suggestion_id=sid,
                context=authorized_task_context,
                message=msg,
                suggestion_text=msg,
                action_preview="deploy_to_staging",
                confidence=0.85,
                requires_confirmation=True,
            )

        if "commit" in current_event.lower():
            msg = "New commit registered. Would you like to run automated tests?"
            return ProactiveSuggestion(
                suggestion_id=sid,
                context=authorized_task_context,
                message=msg,
                suggestion_text=msg,
                action_preview="run_tests",
                confidence=0.75,
                requires_confirmation=True,
            )

        return None

    @classmethod
    def anticipate_workflow_need(
        cls,
        user_id: str,
        recent_actions: List[str],
        context: Dict[str, Any],
    ) -> ProactiveSuggestion:
        """Evaluate recent developer actions and anticipate next step without sensitive inferences (Spec 88, 93)."""
        ctx_str = str(context).lower()
        actions_str = " ".join(recent_actions).lower()

        # Check anti-creepy constraints
        for forbidden in cls.FORBIDDEN_SENSITIVE_DOMAINS:
            if forbidden in ctx_str or forbidden in actions_str:
                raise CreepyInferenceError(
                    f"Proactive anticipation is strictly prohibited on sensitive personal domain '{forbidden}' (Spec 89, 90)."
                )

        sid = f"sug_{uuid.uuid4().hex[:8]}"
        if any("pass" in a or "ci" in a for a in recent_actions):
            msg = "You usually deploy after CI passes. CI just passed; would you like to prepare deployment?"
            action = "prepare_deployment"
        else:
            msg = "Recent code updates detected. Run tests or draft release notes?"
            action = "run_test_suite"

        return ProactiveSuggestion(
            suggestion_id=sid,
            context=f"user:{user_id}:proj:{context.get('project', 'default')}",
            message=msg,
            suggestion_text=msg,
            action_preview=action,
            confidence=0.85,
            requires_confirmation=True,
        )
