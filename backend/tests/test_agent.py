"""Tests for Kairo core agent logic, prompt construction, and routing integration."""

from typing import AsyncIterator, List, Optional
import pytest

from app.agents.core import KAIRO_SYSTEM_PROMPT, AgentResponse, KairoAgent
from app.models.provider import ChatMessage, MessageRole, ModelProvider
from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry
from app.models.router import ModelRouter


class MockModelProvider(ModelProvider):
    """Mock provider recording received messages and returning predetermined outputs."""

    def __init__(self, response_text: str = "Mocked AI response", stream_chunks: Optional[List[str]] = None):
        self.response_text = response_text
        self.stream_chunks = stream_chunks or ["Mocked", " AI", " response"]
        self.received_messages: List[ChatMessage] = []
        self.received_model: Optional[str] = None

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        self.received_messages = messages
        self.received_model = model
        return self.response_text

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        self.received_messages = messages
        self.received_model = model
        for chunk in self.stream_chunks:
            yield chunk


@pytest.mark.asyncio
async def test_kairo_agent_injects_system_prompt() -> None:
    """Verify KairoAgent includes Kairo system persona and user message."""
    mock_provider = MockModelProvider(response_text="Ready to help.")
    agent = KairoAgent(provider=mock_provider)

    result = await agent.process_message("Hello Kairo")

    assert result == "Ready to help."
    assert result.message == "Ready to help."
    assert len(mock_provider.received_messages) == 2

    # System instruction
    assert mock_provider.received_messages[0].role == MessageRole.SYSTEM
    assert mock_provider.received_messages[0].content == KAIRO_SYSTEM_PROMPT
    assert "autonomous personal AI assistant" in mock_provider.received_messages[0].content

    # User message
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
    assert mock_provider.received_messages[0].role == MessageRole.SYSTEM
    assert mock_provider.received_messages[1].role == MessageRole.USER


@pytest.mark.asyncio
async def test_kairo_agent_with_router_capability_selection() -> None:
    """Verify KairoAgent queries router for requested capability and passes model ID."""
    registry = ModelRegistry()
    registry.register_model(ModelDefinition(id="general-model", capabilities={ModelCapability.GENERAL}, priority=10))
    registry.register_model(ModelDefinition(id="coder-model", capabilities={ModelCapability.CODING}, priority=50))

    router = ModelRouter(registry=registry, default_model_id="general-model")
    mock_provider = MockModelProvider(response_text="Code solution")
    agent = KairoAgent(provider=mock_provider, router=router)

    # Request with coding capability
    response: AgentResponse = await agent.process_message("Fix this bug", capability=ModelCapability.CODING)

    assert response.message == "Code solution"
    assert response.model == "coder-model"
    assert mock_provider.received_model == "coder-model"


@pytest.mark.asyncio
async def test_kairo_agent_stream_with_metadata() -> None:
    """Verify stream_message_with_metadata resolves model and streams chunks."""
    registry = ModelRegistry()
    registry.register_model(ModelDefinition(id="fast-model", capabilities={ModelCapability.FAST}, priority=30))
    router = ModelRouter(registry=registry, default_model_id="fast-model")

    mock_provider = MockModelProvider(stream_chunks=["Fast", " response"])
    agent = KairoAgent(provider=mock_provider, router=router)

    model_id, stream = await agent.stream_message_with_metadata("Quick question", capability=ModelCapability.FAST)
    assert model_id == "fast-model"

    tokens = [chunk async for chunk in stream]
    assert tokens == ["Fast", " response"]


def test_deterministic_capability_detector() -> None:
    """Verify the deterministic heuristic routes common keyword patterns."""
    assert KairoAgent.detect_capability("How do I fix this python syntax error?") == ModelCapability.CODING
    assert KairoAgent.detect_capability("Please prove this theorem step by step") == ModelCapability.REASONING
    assert KairoAgent.detect_capability("Can you inspect this photo or image?") == ModelCapability.VISION
    assert KairoAgent.detect_capability("Give me a quick summary in one word") == ModelCapability.FAST
    assert KairoAgent.detect_capability("Hello Kairo, how are you?") == ModelCapability.GENERAL
