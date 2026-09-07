"""Tests for Kairo core agent logic and prompt construction."""

from typing import AsyncIterator, List, Optional
import pytest

from app.agents.core import KAIRO_SYSTEM_PROMPT, KairoAgent
from app.models.provider import ChatMessage, MessageRole, ModelProvider


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
