"""Safety guards, prompt-injection sanitization, secret scrubbing, and risk-aware disambiguation for context."""

import logging
import re

from app.agents.policies import AgentSecurityPolicy
from app.context.schemas import ContextItem
from app.memory.sanitizer import MemorySanitizer

logger = logging.getLogger("kairo.context.safety")


class ContextSafetyGuard:
    """Enforces safety, prompt sanitization, secret redaction, and disambiguation boundaries."""

    # Keywords indicating side-effecting or potentially risky user requests
    RISKY_INTENT_PATTERNS = [
        re.compile(
            r"\b(push|commit|deploy|release|delete|drop|wipe|remove|kill|stop|destroy|execute|run\s+tests?)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(write|create|update|modify|merge|pull\s+request|pr)\b", re.IGNORECASE),
    ]

    @classmethod
    def is_risky_intent(cls, user_message: str) -> bool:
        """Detect whether a query asks for side-effecting, mutative, or destructive actions."""
        if not user_message:
            return False
        return any(pat.search(user_message) for pat in cls.RISKY_INTENT_PATTERNS)

    @classmethod
    def sanitize_item(cls, item: ContextItem) -> ContextItem | None:
        """Filter out credentials and sanitize untrusted text before injecting into model context."""
        content = item.content

        # 1. Secret / Credential check
        if MemorySanitizer.contains_sensitive_data(content):
            logger.warning(
                "Context item '%s' contains sensitive credentials; scrubbing before injection.", item.title
            )
            content = MemorySanitizer.sanitize(content)

        # 2. Prompt injection defense on untrusted content
        sanitized_content = AgentSecurityPolicy.sanitize_untrusted_input(content)

        return ContextItem(
            source_type=item.source_type,
            source_id=item.source_id,
            title=item.title,
            content=sanitized_content,
            relevance_score=item.relevance_score,
            confidence=item.confidence,
            timestamp=item.timestamp,
            provenance=item.provenance,
            reason=item.reason,
        )

    @classmethod
    def check_project_ambiguity(
        cls,
        user_message: str,
        matching_projects: list[str],
    ) -> tuple[bool, str | None]:
        """Detect if multiple projects match a risky command, requiring explicit clarification.

        Returns (requires_disambiguation, clarification_prompt).
        """
        if len(matching_projects) <= 1:
            return False, None

        # For risky actions (push, delete, execute), require explicit target
        if cls.is_risky_intent(user_message):
            prompt = (
                f"You have multiple projects that match your request ({', '.join(matching_projects)}). "
                f"To prevent unintended actions, please specify which project you would like to target."
            )
            return True, prompt

        # For harmless read-only requests, best-effort resolution is allowed
        return False, None
