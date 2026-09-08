"""Tests for Kairo core agent logic, prompt construction, routing, and tool iteration loop."""

from collections.abc import AsyncIterator
from typing import Any

import pytest

from app.agents.core import KAIRO_SYSTEM_PROMPT, AgentResponse, KairoAgent
from app.models.provider import (
    ChatMessage,
    MessageRole,
    ModelProvider,
    ProviderResponse,
)
from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry
from app.models.router import ModelRouter
from app.tools.builtin.calculator import CalculatorTool
from app.tools.builtin.datetime import DateTimeTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall


class MockModelProvider(ModelProvider):
    """Mock provider recording received messages and returning predetermined outputs."""

    def __init__(self, response_text: str = "Mocked AI response", stream_chunks: list[str] | None = None):
        self.response_text = response_text
        self.stream_chunks = stream_chunks or ["Mocked", " AI", " response"]
        self.received_messages: list[ChatMessage] = []
        self.received_model: str | None = None
        self.received_tools: list[dict[str, Any]] | None = None

    async def generate_response(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ProviderResponse:
        self.received_messages = list(messages)
        self.received_model = model
        self.received_tools = tools
        return ProviderResponse(content=self.response_text, model=model)

    async def stream_response(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        self.received_messages = list(messages)
        self.received_model = model
        self.received_tools = tools
        for chunk in self.stream_chunks:
            yield chunk


class ScriptedToolCallingProvider(ModelProvider):
    """Mock provider returning scripted sequence of responses to simulate multi-turn tool loops."""

    def __init__(self, responses: list[ProviderResponse]):
        self.responses = list(responses)
        self.call_history: list[list[ChatMessage]] = []
        self.current_step = 0

    async def generate_response(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> ProviderResponse:
        self.call_history.append(list(messages))
        if self.current_step < len(self.responses):
            resp = self.responses[self.current_step]
            self.current_step += 1
            return resp
        return ProviderResponse(content="Final default response")

    async def stream_response(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        yield "streamed output"


@pytest.mark.asyncio
async def test_kairo_agent_injects_system_prompt() -> None:
    """Verify KairoAgent includes Kairo system persona and user message."""
    mock_provider = MockModelProvider(response_text="Ready to help.")
    agent = KairoAgent(provider=mock_provider)

    result = await agent.process_message("Hello Kairo")

    assert result == "Ready to help."
    assert result.message == "Ready to help."
    assert len(mock_provider.received_messages) == 2

    assert mock_provider.received_messages[0].role == MessageRole.SYSTEM
    assert mock_provider.received_messages[0].content == KAIRO_SYSTEM_PROMPT
    assert mock_provider.received_messages[1].role == MessageRole.USER
    assert mock_provider.received_messages[1].content == "Hello Kairo"


@pytest.mark.asyncio
async def test_kairo_agent_stream_message() -> None:
    """Verify KairoAgent streams chunks from provider."""
    mock_provider = MockModelProvider(stream_chunks=["Hi", " there!"])
    agent = KairoAgent(provider=mock_provider)

    chunks = []
    async for chunk in agent.stream_message("Hi"):
        chunks.append(chunk)

    assert chunks == ["Hi", " there!"]
    assert len(mock_provider.received_messages) == 2


@pytest.mark.asyncio
async def test_kairo_agent_with_router_capability_selection() -> None:
    """Verify KairoAgent queries router for requested capability and passes model ID."""
    registry = ModelRegistry()
    registry.register_model(
        ModelDefinition(id="general-model", capabilities={ModelCapability.GENERAL}, priority=10)
    )
    registry.register_model(
        ModelDefinition(id="coder-model", capabilities={ModelCapability.CODING}, priority=50)
    )

    router = ModelRouter(registry=registry, default_model_id="general-model")
    mock_provider = MockModelProvider(response_text="Code solution")
    agent = KairoAgent(provider=mock_provider, router=router)

    response: AgentResponse = await agent.process_message("Fix this bug", capability=ModelCapability.CODING)

    assert response.message == "Code solution"
    assert response.model == "coder-model"
    assert mock_provider.received_model == "coder-model"


@pytest.mark.asyncio
async def test_kairo_agent_executes_tool_and_passes_result() -> None:
    """Ensure KairoAgent executes requested calculator tool and passes result back to model."""
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_executor = ToolExecutor(registry=tool_registry)

    # Step 1: Model requests calculator tool
    # Step 2: Model returns final answer after seeing tool output
    provider = ScriptedToolCallingProvider(
        responses=[
            ProviderResponse(
                tool_calls=[ToolCall(id="call_1", name="calculator", arguments={"expression": "15 * 4"})]
            ),
            ProviderResponse(content="15 * 4 is 60."),
        ]
    )

    agent = KairoAgent(
        provider=provider,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
    )

    response = await agent.process_message("What is 15 * 4?")

    assert response.message == "15 * 4 is 60."
    assert len(response.tools_used) == 1
    assert response.tools_used[0].tool == "calculator"
    assert response.tools_used[0].status == "success"
    assert response.tools_used[0].verification_status == "verified"

    # Verify conversation history sent to provider on second step
    second_step_messages = provider.call_history[1]
    tool_msg = next(m for m in second_step_messages if m.role == MessageRole.TOOL)
    assert tool_msg.tool_call_id == "call_1"
    assert "60" in tool_msg.content


@pytest.mark.asyncio
async def test_kairo_agent_multiple_sequential_tool_calls() -> None:
    """Ensure KairoAgent supports multiple sequential tool executions in a loop."""
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_registry.register(DateTimeTool())
    tool_executor = ToolExecutor(registry=tool_registry)

    provider = ScriptedToolCallingProvider(
        responses=[
            ProviderResponse(
                tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expression": "2 + 2"})]
            ),
            ProviderResponse(tool_calls=[ToolCall(id="c2", name="datetime", arguments={"timezone": "UTC"})]),
            ProviderResponse(content="Both calculations and time check complete."),
        ]
    )

    agent = KairoAgent(
        provider=provider,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
    )

    response = await agent.process_message("Calculate 2+2 and check time")
    assert response.message == "Both calculations and time check complete."
    assert len(response.tools_used) == 2
    assert response.tools_used[0].tool == "calculator"
    assert response.tools_used[1].tool == "datetime"


@pytest.mark.asyncio
async def test_kairo_agent_max_tool_iterations_limit() -> None:
    """Ensure KairoAgent stops safely when max tool iterations is reached."""
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_executor = ToolExecutor(registry=tool_registry)

    # Infinite loop simulation: provider always requests a tool call
    infinite_calls = [
        ProviderResponse(
            tool_calls=[ToolCall(id=f"call_{i}", name="calculator", arguments={"expression": "1 + 1"})]
        )
        for i in range(10)
    ]
    provider = ScriptedToolCallingProvider(responses=infinite_calls)

    agent = KairoAgent(
        provider=provider,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
        max_tool_iterations=3,
    )

    response = await agent.process_message("Infinite loop test")
    assert "maximum number of tool iterations (3)" in response.message
    assert len(response.tools_used) == 3


@pytest.mark.asyncio
async def test_kairo_agent_tool_failure_handled_safely() -> None:
    """Ensure tool execution error is fed back to model cleanly."""
    tool_registry = ToolRegistry()
    tool_registry.register(CalculatorTool())
    tool_executor = ToolExecutor(registry=tool_registry)

    provider = ScriptedToolCallingProvider(
        responses=[
            ProviderResponse(
                tool_calls=[ToolCall(id="call_err", name="calculator", arguments={"expression": "10 / 0"})]
            ),
            ProviderResponse(content="You cannot divide by zero."),
        ]
    )

    agent = KairoAgent(
        provider=provider,
        tool_registry=tool_registry,
        tool_executor=tool_executor,
    )

    response = await agent.process_message("Compute 10 / 0")
    assert response.message == "You cannot divide by zero."
    assert len(response.tools_used) == 1
    assert response.tools_used[0].status == "failed"


def test_deterministic_capability_detector() -> None:
    """Verify the deterministic heuristic routes common keyword patterns."""
    assert KairoAgent.detect_capability("How do I fix this python syntax error?") == ModelCapability.CODING
    assert KairoAgent.detect_capability("Please prove this theorem step by step") == ModelCapability.REASONING
    assert KairoAgent.detect_capability("Can you inspect this photo or image?") == ModelCapability.VISION
    assert KairoAgent.detect_capability("Give me a quick summary in one word") == ModelCapability.FAST
    assert KairoAgent.detect_capability("Hello Kairo, how are you?") == ModelCapability.GENERAL
