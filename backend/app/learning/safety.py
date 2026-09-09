"""Safety boundary enforcement and anti-poisoning defenses for Kairo Learning Engine (Task 43)."""

from __future__ import annotations

import logging
from typing import Any

from app.learning.strategies import Strategy

logger = logging.getLogger("kairo.learning.safety")


class LearningSafetyGuard:
    """Enforces absolute security boundaries and anti-poisoning constraints (Spec 160-173)."""

    PROHIBITED_INJECTION_PHRASES = [
        "ignore previous instructions",
        "bypass security",
        "disable verification",
        "grant root access",
        "override policy",
        "skip approval",
        "promote this strategy unconditionally",
    ]

    PROHIBITED_SECURITY_KEYS = [
        "security_policy",
        "authorization_rules",
        "approval_requirements",
        "audit_history",
        "system_identity",
        "emergency_stop",
    ]

    @classmethod
    def check_signal_safety(cls, text_content: str) -> tuple[bool, str]:
        """Check if incoming feedback or observation contains prompt injection or policy overrides (Spec 161, 168)."""
        lower = text_content.lower()
        for phrase in cls.PROHIBITED_INJECTION_PHRASES:
            if phrase in lower:
                logger.warning("Rejected learning input containing prohibited override phrase: '%s'", phrase)
                return False, f"Blocked: Learning input contains prohibited policy override instruction ('{phrase}')."
        return True, "OK"

    @classmethod
    def check_strategy_safety(cls, strategy: Strategy) -> tuple[bool, str]:
        """Verify that a candidate strategy does not attempt to modify security or policy (Spec 170, 171)."""
        description_lower = strategy.description.lower()
        domain_lower = strategy.domain.lower()

        # Cannot target security or governance domains
        if domain_lower in ["security", "policy", "authorization", "audit", "governance"]:
            return False, f"Blocked: Learning engine cannot optimize core {domain_lower} subsystem."

        # Cannot contain prohibited terms
        for key in cls.PROHIBITED_SECURITY_KEYS:
            if key in description_lower:
                return False, f"Blocked: Candidate strategy attempts to manipulate protected subsystem '{key}'."

        return True, "Strategy satisfies safety constraints."

    @classmethod
    def prevent_verification_bypass(cls, candidate_strategy: Strategy, baseline_strategy: Strategy | None = None) -> tuple[bool, str]:
        """Prevent reward hacking that improves latency by dropping required verification (Spec 110-113)."""
        if baseline_strategy:
            if candidate_strategy.verification_rate < (baseline_strategy.verification_rate - 0.10):
                return False, "Blocked reward hacking: Candidate strategy significantly reduces verification coverage."

        return True, "Verification coverage maintained."
