"""Security policies, risk evaluation, and high-impact target boundaries (Spec 28, 38, 43, 44, 111-120)."""

import logging
import re
from typing import Any

from app.intent.schemas import IntentRiskLevel, IntentType, ResolutionMethod

logger = logging.getLogger("kairo.intent.policies")


class IntentPolicyEngine:
    """Evaluates intent risk levels and enforces non-negotiable security boundaries."""

    # High-impact resource names and keywords that prohibit fuzzy matching (Spec 28)
    HIGH_IMPACT_KEYWORDS = {
        "prod",
        "production",
        "payment",
        "billing",
        "security",
        "delete_account",
        "reset",
        "wipe",
        "firewall",
        "secret",
        "credential",
    }

    # High-impact intent categories
    HIGH_IMPACT_TYPES = {
        IntentType.DELETE,
        IntentType.CONTROL,
    }

    @classmethod
    def evaluate_risk(
        cls,
        intent_type: IntentType,
        target_name: str | None = None,
        environment: str | None = None,
        is_destructive: bool = False,
    ) -> IntentRiskLevel:
        """
        Determines the intrinsic risk level of an intent.
        INVARIANT: Risk is independent of confidence.
        """
        env_lower = (environment or "").lower()
        target_lower = (target_name or "").lower()

        # Critical risk: targeting production environment or destructive actions on vital resources
        if "prod" in env_lower or "production" in env_lower:
            return IntentRiskLevel.CRITICAL

        if any(kw in target_lower for kw in cls.HIGH_IMPACT_KEYWORDS) and is_destructive:
            return IntentRiskLevel.CRITICAL

        if intent_type == IntentType.DELETE:
            return IntentRiskLevel.HIGH

        if intent_type in (IntentType.APPROVE, IntentType.CONTROL):
            return IntentRiskLevel.HIGH

        if intent_type == IntentType.TASK:
            # Check if task specifies destructive / deployment keywords
            if any(w in target_lower for w in ["deploy", "drop", "purge", "restart"]):
                return IntentRiskLevel.HIGH
            return IntentRiskLevel.NORMAL

        if intent_type in (IntentType.UPDATE, IntentType.CREATE, IntentType.AUTOMATE):
            return IntentRiskLevel.NORMAL

        # Read-only or safe operations
        return IntentRiskLevel.LOW

    @classmethod
    def is_fuzzy_match_allowed(
        cls,
        target_candidate: str,
        environment: str | None = None,
    ) -> bool:
        """
        Spec 28: Never fuzzy-resolve high-impact targets.
        Require exact / explicit matching.
        """
        t_lower = target_candidate.lower()
        e_lower = (environment or "").lower()

        if "prod" in e_lower or "production" in e_lower:
            return False

        if any(kw in t_lower for kw in cls.HIGH_IMPACT_KEYWORDS):
            return False

        return True

    @classmethod
    def validate_cross_user_access(
        cls,
        authenticated_user_id: str,
        resource_owner_id: str | None,
        resource_type: str = "resource",
    ) -> bool:
        """
        Spec 118: If command references another user's object, DENIED.
        Do not reveal whether object exists.
        """
        if resource_owner_id is None:
            return True
        if authenticated_user_id != resource_owner_id:
            logger.warning(
                "Cross-user access denied: user '%s' attempted reference to %s owned by '%s'",
                authenticated_user_id,
                resource_type,
                resource_owner_id,
            )
            return False
        return True

    @classmethod
    def extract_negations_and_hard_constraints(cls, text: str) -> list[str]:
        """
        Spec 100, 105: Preserves negations like "Don't deploy to production", "Don't touch backend".
        Extracts them as hard constraints that must never be violated.
        """
        negations: list[str] = []
        patterns = [
            re.compile(r"\b(don'?t|do\s+not|never|exclude|without)\s+([a-zA-Z0-9_\-\s]{3,30})\b", re.IGNORECASE),
            re.compile(r"\b(no\s+(production|prod|deletions|drops))\b", re.IGNORECASE),
        ]
        for pat in patterns:
            for match in pat.finditer(text):
                negations.append(match.group(0).strip())

        return list(dict.fromkeys(negations))
