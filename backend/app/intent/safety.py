"""Intent Safety Guardrails, Prompt Injection Defense, and Tenant Boundary Protection (Task 48)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger("kairo.intent.safety")


class IntentSecurityViolation(PermissionError):
    """Raised when intent engine detects injection, privilege escalation, or cross-tenant contamination (Spec 163-178)."""


class IntentSafetyGuard:
    """Enforces absolute security, identity, and isolation boundaries around intent formulation (Spec 163-178).
    
    CRITICAL INVARIANTS:
    1. Prompt injection defense (Spec 164): Retrieved docs/web pages cannot command 'User wants X'.
    2. Third-party instruction separation (Spec 166): Treat external instructions as data unless explicitly requested.
    3. Cross-user isolation (Spec 169): Never merge intent across users.
    4. Cross-project isolation (Spec 170): Never infer project scope from unrelated project history.
    5. Destructive action gating (Spec 111): Never guess ambiguous targets for delete operations.
    """

    INJECTION_PATTERNS = [
        re.compile(r"\b(system\s+override|ignore\s+previous\s+instructions|user\s+wants\s+you\s+to\s+delete)\b", re.IGNORECASE),
        re.compile(r"\b(grant\s+admin|bypass\s+policy|elevate\s+privileges)\b", re.IGNORECASE),
        re.compile(r"\b(drop\s+database\s+all|delete\s+all\s+records\s+without\s+confirm)\b", re.IGNORECASE),
    ]

    @classmethod
    def validate_raw_input_safety(cls, text: str = "", source: str = "DIRECT_USER", raw_text: Optional[str] = None) -> None:
        """Enforce Spec 163, 164, 166: Reject prompt injection and unauthenticated external commands."""
        input_text = raw_text if raw_text is not None else text
        for pat in cls.INJECTION_PATTERNS:
            if pat.search(input_text):
                logger.critical("INTENT SECURITY VIOLATION: Suspicious directive detected in input: '%s'", input_text)
                raise IntentSecurityViolation(
                    "Security violation: Input contains prohibited prompt injection or privilege escalation directive."
                )

        if source in ("EXTERNAL_UNTRUSTED_CONTENT", "EXTERNAL_WEB_FETCH", "THIRD_PARTY") or "EXTERNAL" in source:
            # Third-party data cannot issue system instructions (Spec 166)
            logger.warning("Rejected attempt to extract intent directly from untrusted external content")
            raise IntentSecurityViolation(
                "Untrusted external content is treated strictly as data and cannot define user intent (Spec 166)."
            )

    @classmethod
    def enforce_user_isolation(cls, requesting_user_id: str, intent_user_id: str) -> bool:
        """Enforce Spec 169: Cross-user intent isolation."""
        if intent_user_id != "*" and requesting_user_id != intent_user_id:
            logger.critical("CROSS-USER INTENT LEAK ATTEMPT: User '%s' requested intent of '%s'", requesting_user_id, intent_user_id)
            raise IntentSecurityViolation(
                f"Access denied: Intent belongs to user '{intent_user_id}'."
            )
        return True

    @classmethod
    def enforce_project_isolation(cls, current_project_id: str, target_project_id: str) -> bool:
        """Enforce Spec 170: Cross-project intent isolation."""
        if target_project_id != "*" and current_project_id != target_project_id:
            logger.critical("CROSS-PROJECT LEAK ATTEMPT: Project '%s' accessed scope of '%s'", current_project_id, target_project_id)
            raise IntentSecurityViolation(
                f"Access denied: Cannot mutate scope belonging to project '{target_project_id}' from '{current_project_id}'."
            )
        return True

    @classmethod
    def assert_destructive_target_unambiguous(cls, target_name: Optional[str], candidate_count: int) -> None:
        """Enforce Spec 110, 111: Never resolve destructive target ambiguity by guessing."""
        if not target_name or candidate_count != 1:
            logger.critical("SAFETY VIOLATION: Attempted destructive action with ambiguous target (candidates=%d)", candidate_count)
            raise IntentSecurityViolation(
                "Destructive action strictly requires an explicit, unambiguous target. Guessing is forbidden (Spec 111)."
            )

    @classmethod
    def check_urgency_authority_bypass(cls, urgency_level: str, has_approval: bool) -> bool:
        """Enforce Spec 40: Urgency != Authority. 'URGENT' does not bypass authorization or approval."""
        return has_approval

    @classmethod
    def check_confidence_authorization(cls, confidence: float, action_requires_approval: bool, has_approval: bool) -> bool:
        """Enforce Spec 64: Confidence != Authorization. High confidence does not authorize execution."""
        if action_requires_approval and not has_approval:
            return False
        return True

    @classmethod
    def validate_destructive_target(cls, target_name: Optional[str], candidate_count: int) -> bool:
        """Enforce Spec 111: Destructive targets must be explicit and unambiguous."""
        if not target_name or candidate_count != 1:
            return False
        return True
