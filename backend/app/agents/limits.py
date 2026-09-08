"""Limits, concurrency bounds, and tool call budget tracking for Multi-Agent Orchestration."""

import logging
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger("kairo.agents.limits")


class AgentLimitExceededError(Exception):
    """Raised when an agent execution budget or threshold is exceeded."""


class AgentToolLimitExceededError(AgentLimitExceededError):
    """Raised when an agent or supervisor request exceeds allowed tool call limits."""


class AgentTimeoutError(AgentLimitExceededError):
    """Raised when an agent task exceeds execution deadline."""


class AgentBudgetTracker:
    """Tracks and enforces tool calls and token budgets across specialist tasks in a supervisor run."""

    def __init__(
        self,
        max_tool_calls_per_agent: int | None = None,
        max_total_tool_calls: int | None = None,
        max_tokens_per_task: int | None = None,
        max_total_tokens: int | None = None,
    ) -> None:
        cfg = get_settings()
        self.max_tool_calls_per_agent = (
            max_tool_calls_per_agent
            if max_tool_calls_per_agent is not None
            else getattr(cfg, "KAIRO_MAX_AGENT_TOOL_CALLS", 20)
        )
        self.max_total_tool_calls = (
            max_total_tool_calls
            if max_total_tool_calls is not None
            else getattr(cfg, "KAIRO_MAX_TOTAL_AGENT_TOOL_CALLS", 50)
        )
        self.max_tokens_per_task = max_tokens_per_task or getattr(
            cfg, "KAIRO_MAX_AGENT_TOKENS_PER_TASK", None
        )
        self.max_total_tokens = max_total_tokens or getattr(cfg, "KAIRO_MAX_TOTAL_AGENT_TOKENS", None)

        self._agent_tool_calls: dict[str, int] = {}
        self._total_tool_calls: int = 0
        self._agent_tokens: dict[str, int] = {}
        self._total_tokens: int = 0

    def record_tool_call(self, agent_name: str) -> int:
        """Increment and validate tool call count for an agent.

        Raises AgentToolLimitExceededError if per-agent or total limit is reached.
        """
        agent_count = self._agent_tool_calls.get(agent_name, 0)
        if agent_count >= self.max_tool_calls_per_agent:
            raise AgentToolLimitExceededError(
                f"Agent '{agent_name}' exceeded maximum allowed tool calls ({self.max_tool_calls_per_agent})."
            )

        if self._total_tool_calls >= self.max_total_tool_calls:
            raise AgentToolLimitExceededError(
                f"Supervisor orchestration exceeded maximum total tool calls ({self.max_total_tool_calls})."
            )

        self._agent_tool_calls[agent_name] = agent_count + 1
        self._total_tool_calls += 1
        return self._agent_tool_calls[agent_name]

    def record_tokens(self, agent_name: str, total_tokens: int) -> None:
        """Record model token usage and validate budgets if configured."""
        self._agent_tokens[agent_name] = self._agent_tokens.get(agent_name, 0) + total_tokens
        self._total_tokens += total_tokens

        if self.max_tokens_per_task and self._agent_tokens[agent_name] > self.max_tokens_per_task:
            raise AgentLimitExceededError(
                f"Agent '{agent_name}' exceeded token limit ({self.max_tokens_per_task})."
            )

        if self.max_total_tokens and self._total_tokens > self.max_total_tokens:
            raise AgentLimitExceededError(
                f"Supervisor run exceeded total token limit ({self.max_total_tokens})."
            )

    def get_agent_tool_calls(self, agent_name: str) -> int:
        """Return total tool calls invoked by a specific agent."""
        return self._agent_tool_calls.get(agent_name, 0)

    @property
    def total_tool_calls(self) -> int:
        """Return total tool calls across all orchestrated agents."""
        return self._total_tool_calls

    def to_dict(self) -> dict[str, Any]:
        """Summary metrics dictionary."""
        return {
            "total_tool_calls": self._total_tool_calls,
            "agent_tool_calls": dict(self._agent_tool_calls),
            "total_tokens": self._total_tokens,
            "agent_tokens": dict(self._agent_tokens),
        }
