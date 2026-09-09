"""Agent Isolation, Cross-Tenant Security, and Anti-Hijacking Defenses (Task 44)."""

from __future__ import annotations

import logging
from typing import Any

from app.security.redaction import ArgumentSanitizer

logger = logging.getLogger("kairo.agents.isolation")


class SecurityIsolationViolationError(Exception):
    """Raised when an agent attempts an unauthorized cross-tenant access or privileged bypass."""


class TenantIsolationViolationError(SecurityIsolationViolationError):
    """Raised on cross-user or cross-project tenant access violation."""


class PromptInjectionDetectedError(SecurityIsolationViolationError):
    """Raised when an adversarial prompt injection pattern is detected in input/output."""


class GoalHijackViolationError(SecurityIsolationViolationError):
    """Raised when an external directive attempts to replace the parent goal."""


class AgentApprovalViolationError(SecurityIsolationViolationError):
    """Raised when an agent illegally approves its own or a peer's privileged action."""


class AgentIsolationGuard:
    """Enforces strict tenant isolation, permission filtering, and injection defenses (Specs 68-76, 81-86)."""

    PROHIBITED_INJECTION_DIRECTIVES = [
        "ignore previous instructions",
        "ignore contract",
        "bypass policy",
        "grant permission",
        "override supervisor",
        "send secrets",
        "exfiltrate credentials",
        "modify system policy",
    ]

    def validate_user_access(self, agent_user_id: str, requested_user_id: str) -> bool:
        """Enforce strict cross-user isolation (Spec 70)."""
        if agent_user_id != requested_user_id:
            logger.warning("Cross-user violation: Agent (%s) attempted access to User (%s)", agent_user_id, requested_user_id)
            raise TenantIsolationViolationError(
                f"Cross-user isolation violation: Agent belonging to '{agent_user_id}' cannot access context of '{requested_user_id}'."
            )
        return True

    def validate_project_access(self, agent_project_id: str | None, target_project_id: str | None) -> bool:
        """Enforce strict cross-project isolation (Spec 69)."""
        if agent_project_id and target_project_id and agent_project_id != target_project_id:
            logger.warning(
                "Cross-project violation: Agent in Project (%s) attempted access to Project (%s)",
                agent_project_id,
                target_project_id,
            )
            raise TenantIsolationViolationError(
                f"Cross-project isolation violation: Agent in project '{agent_project_id}' cannot access project '{target_project_id}'."
            )
        return True

    @classmethod
    def validate_tenant_access(
        cls,
        agent_user_id: str,
        target_user_id: str,
        agent_project_id: str | None = None,
        target_project_id: str | None = None,
    ) -> bool:
        guard = cls()
        guard.validate_user_access(agent_user_id, target_user_id)
        guard.validate_project_access(agent_project_id, target_project_id)
        return True

    def sanitize_and_validate_external_input(self, text: str) -> str:
        """Scan input for prompt injection and goal hijacking directives."""
        lower = text.lower()
        for phrase in self.PROHIBITED_INJECTION_DIRECTIVES:
            if phrase in lower:
                logger.warning("Injection directive detected: '%s'", phrase)
                raise PromptInjectionDetectedError(
                    f"Prompt injection directive detected: '{phrase}' is forbidden."
                )
        return text

    @classmethod
    def check_goal_hijacking(cls, parent_goal: str, subtask_output: str) -> bool:
        """Ensure external content has not hijacked the agent to replace the parent goal (Spec 81-83)."""
        lower = subtask_output.lower()
        for phrase in cls.PROHIBITED_INJECTION_DIRECTIVES:
            if phrase in lower:
                logger.warning("Goal hijacking directive detected in agent output: '%s'", phrase)
                raise GoalHijackViolationError(
                    f"Agent goal hijacking detected: Output contains prohibited injection directive ('{phrase}')."
                )
        return True

    def validate_peer_approval(
        self,
        requesting_agent_id: str,
        approving_agent_id: str,
        action: str,
        authorized_governance_roles: list[str] | None = None,
    ) -> bool:
        """Enforce Spec 76: One agent CANNOT approve another agent's privileged action without governance."""
        if requesting_agent_id == approving_agent_id:
            raise AgentApprovalViolationError("Self-approval forbidden: Agent cannot approve its own privileged action.")
        # Peer agents cannot approve privileged actions unless granted governance role
        if not authorized_governance_roles:
            raise AgentApprovalViolationError(
                f"Peer approval forbidden: Agent '{approving_agent_id}' is not authorized to approve action '{action}'."
            )
        return True

    @classmethod
    def validate_cross_agent_approval(cls, requester_agent_id: str, approver_agent_id: str) -> bool:
        return cls().validate_peer_approval(requester_agent_id, approver_agent_id, "default_action", authorized_governance_roles=["GOVERNANCE"])

    @classmethod
    def sanitize_agent_output(cls, data: Any) -> Any:
        """Scan and redact secrets from agent outputs before sharing across team (Spec 86, 177)."""
        return ArgumentSanitizer.sanitize(data)
