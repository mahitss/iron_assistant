"""Prediction Safety Guardrails, Prompt Injection Defenses, Tenant Isolation, and Anti-Poisoning (Task 47)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("kairo.prediction.safety")


class PredictionSecurityViolation(Exception):
    """Raised when prediction engine detects poisoning, unauthorized cross-tenant query, or privilege escalation (Spec 149-156, 183-187)."""


class PredictionSafetyGuard:
    """Enforces absolute security boundaries around predictive intelligence (Spec 149-156, 183-198)."""

    @classmethod
    def validate_tenant_boundaries(
        cls,
        prediction_scope_user: str,
        prediction_scope_project: str,
        requesting_user: str,
        requesting_project: str,
    ) -> None:
        """Enforce Spec 101, 102: Cross-user and cross-project prediction data isolation."""
        if prediction_scope_user != "*" and prediction_scope_user != requesting_user:
            logger.critical("CROSS-USER PREDICTION LEAK: user %s attempted access to %s", requesting_user, prediction_scope_user)
            raise PredictionSecurityViolation(f"Access denied: Prediction belongs to user '{prediction_scope_user}'.")

        if prediction_scope_project != "*" and prediction_scope_project != requesting_project:
            logger.critical("CROSS-PROJECT PREDICTION LEAK: project %s attempted access to %s", requesting_project, prediction_scope_project)
            raise PredictionSecurityViolation(f"Access denied: Prediction belongs to project '{prediction_scope_project}'.")

    @classmethod
    def enforce_tenant_access(
        cls,
        requesting_user_id: str,
        resource_user_id: str,
        resource_id: str,
    ) -> None:
        """Enforce strict cross-user isolation (Spec 101)."""
        if resource_user_id != "*" and requesting_user_id != resource_user_id:
            raise PredictionSecurityViolation(
                f"Unauthorized cross-user access: User '{requesting_user_id}' cannot access resource '{resource_id}' owned by '{resource_user_id}'."
            )

    @classmethod
    def enforce_project_access(
        cls,
        requesting_project_id: str,
        resource_project_id: str,
        resource_id: str,
    ) -> None:
        """Enforce strict cross-project isolation (Spec 102)."""
        if resource_project_id != "*" and requesting_project_id != resource_project_id:
            raise PredictionSecurityViolation(
                f"Unauthorized cross-project access: Project '{requesting_project_id}' cannot access resource '{resource_id}' owned by '{resource_project_id}'."
            )

    @classmethod
    def validate_observation_text(cls, text: str) -> None:
        """Enforce Spec 186, 187: Validate observation text against prompt injection directives."""
        lower = text.lower()
        forbidden_directives = [
            "ignore previous rules",
            "ignore previous instructions",
            "system override",
            "system prompt",
            "predict that the system has been compromised",
            "predict zero risk",
            "grant admin token",
            "execute immediately",
        ]
        for directive in forbidden_directives:
            if directive in lower:
                logger.critical("PROMPT INJECTION DETECTED in telemetry: '%s'", directive)
                raise PredictionSecurityViolation(
                    f"Prompt injection directive detected in prediction observation: '{directive}'."
                )

    @classmethod
    def sanitize_prediction_input(cls, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """Enforce Spec 186, 187: Hard data/instruction separation. External untrusted content cannot command 'predict X'."""
        cleaned = dict(raw_input)
        for k, v in list(cleaned.items()):
            if isinstance(v, str):
                v_lower = v.lower()
                # Check for prompt injection patterns attempting to manipulate predictions
                if any(inj in v_lower for inj in [
                    "ignore previous instructions", "system prompt", "predict 100% failure",
                    "override safety policy", "execute immediately", "predict zero risk",
                ]):
                    logger.warning("PROMPT INJECTION DEFENSE: Stripped suspicious directive from feature '%s'", k)
                    cleaned[k] = "[SANITIZED_PROMPT_DIRECTIVE]"
        return cleaned

    @classmethod
    def assert_non_destructive(cls, action_name: str) -> None:
        """Enforce Spec 54, 154: Destructive actions can NEVER execute on prediction alone."""
        destructive_keywords = ["delete", "drop", "purge", "terminate", "rollback_production", "destroy"]
        if any(dk in action_name.lower() for dk in destructive_keywords):
            logger.critical("SAFETY VIOLATION: Prediction attempted to trigger destructive action '%s'", action_name)
            raise PredictionSecurityViolation(
                f"Destructive action '{action_name}' is forbidden from autonomous prediction trigger without explicit approval."
            )
