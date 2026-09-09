"""Autonomy Safety Boundaries, Self-Modification Defenses, and Action Gating (Task 45)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.autonomy.state import ActionClassification, AutonomyLevel

logger = logging.getLogger("kairo.autonomy.safety")


class SafetyViolationError(Exception):
    """Raised when an autonomous execution attempts to breach core safety boundaries or self-modify."""


class AutonomySafetyGuard:
    """Enforces absolute safety constraints, fail-closed defaults, and self-modification prevention (Spec 141-146, 191-196)."""

    PROTECTED_SYSTEM_PATHS = [
        "app/security",
        "app/policy",
        "app/auth",
        "app/audit",
        "app/autonomy/safety.py",
        "app/governance",
    ]

    @classmethod
    def validate_action_against_autonomy_level(
        cls,
        action_class: ActionClassification,
        autonomy_level: AutonomyLevel,
        is_pre_approved: bool = False,
    ) -> bool:
        """Enforce Spec 134-143: Gating of actions by autonomy level."""
        # 1. READ and ANALYZE are allowed across all levels
        if action_class in [ActionClassification.READ, ActionClassification.ANALYZE]:
            return True

        # 2. ASSISTED level requires explicit human approval for any state-mutating action
        if autonomy_level == AutonomyLevel.ASSISTED:
            if not is_pre_approved:
                raise SafetyViolationError(
                    f"Action class '{action_class.value}' blocked under ASSISTED autonomy without user pre-approval."
                )
            return True

        # 3. SUPERVISED level allows WRITE and COMMUNICATE, but DEPLOY, DELETE, and PRIVILEGED require approval
        if autonomy_level == AutonomyLevel.SUPERVISED:
            if action_class in [ActionClassification.DEPLOY, ActionClassification.DELETE, ActionClassification.PRIVILEGED]:
                if not is_pre_approved:
                    raise SafetyViolationError(
                        f"High-consequence action '{action_class.value}' requires explicit human approval under SUPERVISED mode."
                    )
            return True

        # 4. CONDITIONAL level requires pre-approval for PRIVILEGED and DELETE
        if autonomy_level == AutonomyLevel.CONDITIONAL:
            if action_class in [ActionClassification.PRIVILEGED, ActionClassification.DELETE] and not is_pre_approved:
                raise SafetyViolationError(f"Action '{action_class.value}' requires explicit condition verification.")
            return True

        # 5. AUTONOMOUS level allows governed execution, but PRIVILEGED still requires security authorization
        if action_class == ActionClassification.PRIVILEGED and not is_pre_approved:
            raise SafetyViolationError("PRIVILEGED actions cannot be executed autonomously without external security approval.")

        return True

    @classmethod
    def validate_anti_self_modification(cls, target_resource: str, proposed_change: str) -> None:
        """Enforce Spec 191, 195: Kairo cannot modify its own security, authorization, governance, or safety."""
        target_norm = target_resource.replace("\\", "/").lower()
        for protected in cls.PROTECTED_SYSTEM_PATHS:
            if protected in target_norm:
                logger.critical("Self-modification attempt blocked on protected system path: %s", target_resource)
                raise SafetyViolationError(
                    f"ANTI-SELF-MODIFICATION BLOCKED: Autonomy cannot modify core security path '{target_resource}'."
                )

        change_lower = proposed_change.lower()
        prohibited_phrases = [
            "disable security",
            "grant all permissions",
            "bypass policy",
            "disable audit",
            "remove safety guard",
        ]
        for phrase in prohibited_phrases:
            if phrase in change_lower:
                logger.critical("Self-granting privilege attempt blocked: '%s'", phrase)
                raise SafetyViolationError(f"ANTI-SELF-MODIFICATION BLOCKED: Prohibited directive '{phrase}'.")
