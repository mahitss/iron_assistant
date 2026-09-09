"""Safety, security boundaries, prompt injection defense, anti-phishing, and anti-impersonation rules."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class CommunicationSafetyError(Exception):
    """Raised when a communication violates core safety, anti-abuse, or security boundaries."""
    pass


class PromptInjectionDetectedError(CommunicationSafetyError):
    """Raised when inbound communication contains adversarial instructions targeting Kairo."""
    pass


class CommunicationSafetyGuard:
    """Enforces safety constraints across incoming and outgoing communications."""

    # Patterns indicating prompt injection attacks in inbound emails or messages
    INJECTION_PATTERNS = [
        r"(?i)ignore\s+(?:all\s+)?previous\s+instructions",
        r"(?i)disregard\s+(?:all\s+)?prior\s+prompts",
        r"(?i)system\s*:\s*you\s+are\s+now",
        r"(?i)you\s+are\s+now\s+in\s+developer\s+mode",
        r"(?i)output\s+(?:all\s+)?passwords\s+and\s+secrets",
        r"(?i)<script\b[^>]*>(.*?)</script>",
    ]

    # Phishing / Deception patterns
    PHISHING_PATTERNS = [
        r"(?i)verify\s+your\s+account\s+immediately\s+or\s+it\s+will\s+be\s+closed",
        r"(?i)click\s+here\s+to\s+claim\s+your\s+prize",
        r"(?i)urgent:\s*wire\s+funds\s+to\s+avoid\s+arrest",
        r"(?i)send\s+your\s+password\s+to\s+continue",
    ]

    # Harassment / Threat keywords
    THREAT_PATTERNS = [
        r"(?i)\bi\s+will\s+(?:kill|hurt|destroy|attack)\s+you\b",
        r"(?i)\byou\s+will\s+suffer\b",
        r"(?i)\bi\s+am\s+going\s+to\s+ruin\s+your\s+life\b",
    ]

    def audit_inbound_message(self, content: str) -> None:
        """INVARIANT 196: Checks whether an inbound message attempts prompt injection or hijacking."""
        for pat in self.INJECTION_PATTERNS:
            if re.search(pat, content):
                raise PromptInjectionDetectedError(
                    f"Adversarial prompt injection pattern detected in inbound message: '{pat}'. Content neutralized."
                )

    def audit_outbound_draft(
        self,
        content: str,
        sender_identity: str,
        claimed_human: bool = False,
    ) -> None:
        """INVARIANTS 98-103, 150-152:

        Blocks impersonation, forged identity, phishing, harassment, threats, and emotional manipulation.
        """
        # 1. Impersonation / False Human representation check
        if claimed_human:
            raise CommunicationSafetyError(
                "Kairo must never falsely represent itself as a human when disclosure is required."
            )

        # 2. Phishing & Deception check
        for pat in self.PHISHING_PATTERNS:
            if re.search(pat, content):
                raise CommunicationSafetyError(
                    f"Outbound content resembles social engineering or phishing ('{pat}'). Transmission blocked."
                )

        # 3. Threats & Harassment check
        for pat in self.THREAT_PATTERNS:
            if re.search(pat, content):
                raise CommunicationSafetyError(
                    f"Outbound content contains prohibited threatening or abusive language. Transmission blocked."
                )
