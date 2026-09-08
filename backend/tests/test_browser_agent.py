"""Integration tests for Kairo agent executing browser tools and preserving existing capabilities."""

import pytest

from app.agents.core import KairoAgent
from app.models.provider import ModelProvider, ProviderResponse, ToolCall
from app.tools.browser.actions import (
    BrowserInspectTool,
    BrowserNavigateTool,
)
from app.tools.browser.manager import BrowserManager
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry, create_default_tool_registry


class MockModelProvider(ModelProvider):
    """Mock provider allowing sequential response configuration."""

    def __init__(self, responses: list[ProviderResponse]):
        self.responses = list(responses)
        self.call_count = 0

    async def generate_response(self, messages, model=None, stream=False, tools=None):
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return ProviderResponse(content="Final default response.", model="test-model")

    async def stream_response(self, messages, model=None, tools=None):
        yield "Streamed "
        yield "answer."


def test_registry_contains_browser_tools():
    """Verify create_default_tool_registry includes browser tools when enabled."""
    registry = create_default_tool_registry()

    assert registry.has_tool("browser_navigate")
    assert registry.has_tool("browser_inspect")
    assert registry.has_tool("browser_screenshot")
    assert registry.has_tool("browser_click")
    assert registry.has_tool("browser_fill")

    # Built-in tools and web tools remain present
    assert registry.has_tool("calculator")
    assert registry.has_tool("datetime")
    assert registry.has_tool("system_info")
    assert registry.has_tool("web_search")
    assert registry.has_tool("web_fetch")


@pytest.mark.asyncio
async def test_agent_browser_navigate_and_inspect_flow():
    """Verify Kairo executes browser_navigate and browser_inspect in multi-turn tool flow."""
    manager = BrowserManager()
    try:
        session = await manager.get_or_create_session("agent_sess_1")

        # Mock page content
        async def handle_route(route):
            await route.fulfill(
                status=200,
                content_type="text/html",
                body="<html><head><title>Kairo Project Docs</title></head><body><h1>Kairo Overview</h1><p>Autonomous AI Assistant documentation.</p></body></html>",
            )

        await session.page.route("https://docs.kairo.ai", handle_route)

        registry = ToolRegistry()
        nav_tool = BrowserNavigateTool(manager=manager)
        inspect_tool = BrowserInspectTool(manager=manager)
        registry.register(nav_tool)
        registry.register(inspect_tool)

        executor = ToolExecutor(registry=registry)

        # Step 1: Model calls browser_navigate
        call_1 = ProviderResponse(
            content=None,
            model="test-model",
            tool_calls=[
                ToolCall(
                    id="call_nav_1",
                    name="browser_navigate",
                    arguments={"url": "https://docs.kairo.ai"},
                )
            ],
        )

        # Step 2: Model calls browser_inspect
        call_2 = ProviderResponse(
            content=None,
            model="test-model",
            tool_calls=[
                ToolCall(
                    id="call_insp_1",
                    name="browser_inspect",
                    arguments={},
                )
            ],
        )

        # Step 3: Model outputs final answer
        call_3 = ProviderResponse(
            content="The Kairo Overview page describes the Autonomous AI Assistant documentation.",
            model="test-model",
        )

        provider = MockModelProvider([call_1, call_2, call_3])
        agent = KairoAgent(
            provider=provider,
            tool_registry=registry,
            tool_executor=executor,
            memory_extraction_enabled=False,
        )

        resp = await agent.process_message(
            message="Inspect https://docs.kairo.ai and tell me what it is.",
            session_id="agent_sess_1",
        )

        assert "Kairo Overview" in resp.message
        assert len(resp.tools_used) == 2
        assert resp.tools_used[0].tool == "browser_navigate"
        assert resp.tools_used[0].status == "success"
        assert resp.tools_used[1].tool == "browser_inspect"
        assert resp.tools_used[1].status == "success"
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_agent_browser_click_requires_approval():
    """Verify that browser_click requires approval when invoked by agent."""
    registry = create_default_tool_registry()
    executor = ToolExecutor(registry=registry)

    call_click = ProviderResponse(
        content=None,
        model="test-model",
        tool_calls=[
            ToolCall(
                id="call_click_1",
                name="browser_click",
                arguments={"selector": "#confirm-btn"},
            )
        ],
    )
    final_resp = ProviderResponse(
        content="Action requires your approval before proceeding.",
        model="test-model",
    )

    provider = MockModelProvider([call_click, final_resp])
    agent = KairoAgent(
        provider=provider,
        tool_registry=registry,
        tool_executor=executor,
        memory_extraction_enabled=False,
    )

    resp = await agent.process_message(
        message="Click the confirm button",
        session_id="agent_click_sess",
    )

    assert len(resp.tools_used) == 1
    assert resp.tools_used[0].status == "failed"
    assert resp.tools_used[0].verification_status == "denied"
