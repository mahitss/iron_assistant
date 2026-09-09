"""Validation of structured intents, constraints, scopes, and conflicting conditions (Spec 23-29, 104-121)."""

import logging
from typing import Any

from app.intent.policies import IntentPolicyEngine
from app.intent.schemas import (
    IntentConstraints,
    IntentErrorState,
    IntentRiskLevel,
    IntentTarget,
    IntentType,
)

logger = logging.getLogger("kairo.intent.validator")


class IntentValidator:
    """Validates intent structure, entity ownership, parameter completeness, and constraint consistency."""

    @classmethod
    def validate_intent(
        cls,
        intent_type: IntentType,
        target: IntentTarget | None,
        constraints: IntentConstraints,
        authenticated_user_id: str,
        resource_owner_id: str | None = None,
        is_ambiguous: bool = False,
    ) -> tuple[bool, IntentErrorState, str | None]:
        """
        Validates the intent before routing or execution.
        Returns:
            (is_valid, error_state, error_message)
        """
        # 1. Ambiguity blocks execution (Spec 47)
        if is_ambiguous:
            return False, IntentErrorState.WAITING_USER, "Clarification needed before proceeding."

        # 2. Cross-user ownership verification (Spec 118)
        if not IntentPolicyEngine.validate_cross_user_access(
            authenticated_user_id=authenticated_user_id,
            resource_owner_id=resource_owner_id,
        ):
            return False, IntentErrorState.TARGET_UNAUTHORIZED, "Access to the requested resource is denied."

        # 3. Conflicting constraints check (Spec 104, 105)
        # e.g. environment is "staging", but "staging" is in hard negations or disallowed_environments
        if constraints.environment:
            env_clean = constraints.environment.lower()
            if any(env_clean in dis.lower() for dis in constraints.disallowed_environments):
                return (
                    False,
                    IntentErrorState.CONFLICTING_CONSTRAINTS,
                    f"Conflicting constraints: environment '{constraints.environment}' is in disallowed environments.",
                )
            for neg in constraints.hard_negations:
                if env_clean in neg.lower():
                    return (
                        False,
                        IntentErrorState.CONFLICTING_CONSTRAINTS,
                        f"Conflicting constraints: requested environment '{constraints.environment}' contradicts negation '{neg}'.",
                    )

        # 4. High-risk actions require an explicit target (Spec 28, 43)
        if intent_type in (IntentType.DELETE, IntentType.CONTROL):
            if not target or not target.name:
                return False, IntentErrorState.MISSING_PARAMETER, f"Target required for action '{intent_type.value}'."

        return True, IntentErrorState.READY, None
