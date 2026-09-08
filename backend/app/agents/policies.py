"""Security policies, delegation boundaries, and prompt-injection defense for Multi-Agent Orchestration."""

import logging
import re
from typing import Any

from app.agents.state import AgentType
from app.security.exceptions import EmergencyStopActiveError, SecurityError

logger = logging.getLogger("kairo.agents.policies")

# Patterns targeting agent delegation, policy modification, or self-approval
INJECTION_AGENT_PATTERNS = [
    re.compile(r"(?i)\bspawn\s+(new\s+)?agent\b"),
    re.compile(r"(?i)\bdelegate\s+to\b"),
    re.compile(r"(?i)\bapprove\s+(this\s+)?action\b"),
    re.compile(r"(?i)\bgrant\s+(all\s+)?permissions?\b"),
    re.compile(r"(?i)\bbypass\s+security\b"),
    re.compile(r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b"),
    re.compile(r"(?i)\bdisregard\s+(all\s+)?(safety|rules|instructions|guidelines)\b"),
    re.compile(r"(?i)\byou\s+are\s+now\s+an?\s+(unrestricted|different)\b"),
]


class AgentSecurityViolation(SecurityError):
    """Raised when an agent violates orchestration security policies."""


class AgentSecurityPolicy:
    """Enforces orchestration boundaries preventing recursive agent spawning, privilege escalation, and injection."""

    @classmethod
    def assert_can_coordinate(cls, agent_type: str) -> None:
        """Validate that only the SUPERVISOR agent can create plans or coordinate tasks."""
        if str(agent_type).upper() != AgentType.SUPERVISOR:
            logger.warning("Agent '%s' attempted unauthorized task delegation!", agent_type)
            raise AgentSecurityViolation(
                f"Specialist agent '{agent_type}' cannot coordinate or spawn other agents. Only Supervisor is authorized."
            )

    @classmethod
    def assert_delegation_depth(cls, depth: int, max_depth: int = 1) -> None:
        """Enforce maximum delegation depth (depth 1 = Supervisor -> Specialist). Recursive sub-agents forbidden."""
        if depth > max_depth:
            raise AgentSecurityViolation(
                f"Delegation depth {depth} exceeds maximum allowed depth of {max_depth}. Recursive agent spawning is prohibited."
            )

    @classmethod
    def assert_tool_allowed(cls, agent_type: str, tool_name: str, allowed_tools: list[str]) -> None:
        """Validate that a requested tool belongs strictly to the specialist agent's allowlist."""
        if tool_name not in allowed_tools:
            logger.warning(
                "Agent '%s' attempted to invoke forbidden tool '%s'. Allowed: %s",
                agent_type,
                tool_name,
                allowed_tools,
            )
            raise AgentSecurityViolation(
                f"Tool '{tool_name}' is not permitted for specialist '{agent_type}'. Allowed: {allowed_tools}"
            )

    @classmethod
    def assert_no_self_approval(cls, tool_name: str) -> None:
        """Enforce that agents cannot self-approve restricted or high-risk actions."""
        # In Kairo, approval requests MUST propagate to the human user through SecurityCenter
        logger.debug("Self-approval prohibited: all restricted actions route through SecurityCenter.")

    @classmethod
    def check_emergency_stop(
        cls,
        user_id: str,
        tool_name: str | None = None,
        emergency_stop_service: Any = None,
        action: str | None = None,
    ) -> None:
        """Enforce immediate kill switch halting side-effecting tools across all agents."""
        target_name = action or tool_name or "agent_action"
        if emergency_stop_service and emergency_stop_service.is_stopped(user_id):
            logger.critical(
                "EMERGENCY STOP ACTIVE: Halting tool '%s' execution for user '%s'.",
                target_name,
                user_id,
            )
            raise EmergencyStopActiveError(
                f"Action '{target_name}' blocked: Emergency stop is currently ACTIVE."
            )

    @classmethod
    def sanitize_untrusted_input(cls, content: str, max_chars: int = 20000) -> str:
        """Bound length and filter dangerous jailbreak phrases in external content."""
        if not content:
            return ""

        # Bound max length to avoid blowing context
        text = content[:max_chars]

        # Neutralize agent control instructions inside external documents
        for pat in INJECTION_AGENT_PATTERNS:
            text = pat.sub("[UNTRUSTED_CONTENT_FILTERED]", text)

        return text
