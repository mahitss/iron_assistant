"""Unit tests for AgentRegistry, agent specifications, and tool allowlists."""

import pytest

from app.agents.registry import (
    AgentRegistry,
    DuplicateAgentError,
    UnknownAgentError,
    create_default_agent_registry,
)
from app.agents.schemas import AgentDefinition
from app.agents.state import AgentType


def test_default_agent_registry_initialization():
    """Default agent registry must register standard supervisor and specialists."""
    registry = create_default_agent_registry()

    assert registry.has_agent(AgentType.SUPERVISOR)
    assert registry.has_agent(AgentType.RESEARCHER)
    assert registry.has_agent(AgentType.DEVELOPER)
    assert registry.has_agent(AgentType.ANALYST)
    assert registry.has_agent(AgentType.BROWSER)

    # Unknown agent check
    assert not registry.has_agent("HACKER_AGENT")
    with pytest.raises(UnknownAgentError):
        registry.get("HACKER_AGENT")


def test_agent_tool_allowlists():
    """Verify tool allowlists are strictly mapped according to agent responsibilities."""
    registry = create_default_agent_registry()

    researcher = registry.get(AgentType.RESEARCHER)
    assert "web_search" in researcher.allowed_tools
    assert "web_fetch" in researcher.allowed_tools
    assert "browser_click" not in researcher.allowed_tools
    assert "git_status" not in researcher.allowed_tools

    developer = registry.get(AgentType.DEVELOPER)
    assert "git_status" in developer.allowed_tools
    assert "code_search" in developer.allowed_tools
    assert "web_search" not in developer.allowed_tools

    analyst = registry.get(AgentType.ANALYST)
    assert len(analyst.allowed_tools) == 0  # Pure analytical synthesis

    browser = registry.get(AgentType.BROWSER)
    assert "browser_inspect" in browser.allowed_tools
    assert "browser_screenshot" in browser.allowed_tools


def test_duplicate_registration_prevented():
    """Attempting to overwrite or duplicate an existing agent type must be rejected."""
    registry = AgentRegistry()
    registry.register(
        AgentDefinition(
            name="Test",
            agent_type=AgentType.RESEARCHER,
            description="Test",
        )
    )

    with pytest.raises(DuplicateAgentError):
        registry.register(
            AgentDefinition(
                name="Duplicate",
                agent_type=AgentType.RESEARCHER,
                description="Duplicate",
            )
        )
