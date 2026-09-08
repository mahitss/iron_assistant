"""Integration tests for KairoAgent intelligent memory extraction and resilience."""

import json
from typing import AsyncIterator, List, Optional

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.core import KairoAgent
from app.db.session import Base
from app.memory.embeddings import DeterministicEmbeddingProvider
from app.memory.extractor import MemoryExtractor
from app.memory.repository import ConversationRepository
from app.memory.service import MemoryService
from app.models.provider import ChatMessage, ModelProvider, ProviderAPIError, ProviderResponse
from app.tools.builtin.calculator import CalculatorTool
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry
from app.tools.schemas import ToolCall


class ScriptableMockProvider(ModelProvider):
    """Mock provider allowing custom scripted responses for chat and extraction calls."""

    def __init__(self):
        self.chat_responses: List[str] = ["Hello from Kairo."]
        self.chat_call_count = 0
        self.extraction_responses: List[str] = ['{"candidates": []}']
        self.extraction_call_count = 0
        self.fail_chat = False
        self.fail_extraction = False

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> ProviderResponse:
        # Check if this call is an extraction request
        is_extraction = any("Kairo's Memory Extractor" in str(m.content) for m in messages)

        if is_extraction:
            if self.fail_extraction:
                raise ProviderAPIError("Simulated extraction model failure", status_code=500)
            text = self.extraction_responses[self.extraction_call_count % len(self.extraction_responses)]
            self.extraction_call_count += 1
            return ProviderResponse(content=text, model=model or "fast/extractor")

        if self.fail_chat:
            raise ProviderAPIError("Chat model failure", status_code=502)

        text = self.chat_responses[self.chat_call_count % len(self.chat_responses)]
        self.chat_call_count += 1
        return ProviderResponse(content=text, model=model or "chat/model")

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        text = self.chat_responses[self.chat_call_count % len(self.chat_responses)]
        self.chat_call_count += 1
        for word in text.split(" "):
            yield word + " "


@pytest.fixture
async def async_db_session():
    """Provide isolated in-memory SQLite database session for unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def embedding_provider():
    return DeterministicEmbeddingProvider(dimension=64)


@pytest.mark.asyncio
async def test_chat_triggers_extraction_and_persists_memory(
    async_db_session: AsyncSession, embedding_provider
):
    """Verify durable preference is automatically extracted and persisted after turn."""
    provider = ScriptableMockProvider()
    provider.chat_responses = ["I have noted that you prefer dark mode."]
    provider.extraction_responses = [
        json.dumps(
            {
                "candidates": [
                    {
                        "content": "The user prefers dark mode.",
                        "memory_type": "preference",
                        "importance": 0.8,
                        "reason": "User stated preference",
                    }
                ]
            }
        )
    ]

    conv_repo = ConversationRepository(async_db_session)
    mem_service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)
    extractor = MemoryExtractor(provider=provider)

    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
        memory_service=mem_service,
        embedding_provider=embedding_provider,
        memory_extractor=extractor,
        memory_extraction_enabled=True,
    )

    resp = await agent.process_message("I prefer dark mode.", session_id="sess_extract_1")
    assert resp.message == "I have noted that you prefer dark mode."

    # Verify memory was stored in DB
    stored_memories = await mem_service.list_memories()
    assert len(stored_memories) == 1
    assert stored_memories[0].content == "The user prefers dark mode."
    assert stored_memories[0].memory_type == "preference"


@pytest.mark.asyncio
async def test_chat_succeeds_even_when_extraction_fails(async_db_session: AsyncSession, embedding_provider):
    """Verify assistant response is returned cleanly when extraction throws an error."""
    provider = ScriptableMockProvider()
    provider.chat_responses = ["Here is your response."]
    provider.fail_extraction = True  # Extraction will crash

    conv_repo = ConversationRepository(async_db_session)
    mem_service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)
    extractor = MemoryExtractor(provider=provider)

    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
        memory_service=mem_service,
        embedding_provider=embedding_provider,
        memory_extractor=extractor,
        memory_extraction_enabled=True,
    )

    # Chat must succeed and return the assistant response without raising!
    resp = await agent.process_message("Remember this.", session_id="sess_fail_ext")
    assert resp.message == "Here is your response."

    # Assistant message was still persisted in conversation history
    conv = await conv_repo.get_by_session_id("sess_fail_ext")
    messages = await conv_repo.get_recent_messages(conv.id, limit=10)
    assert len(messages) == 2
    assert messages[1].content == "Here is your response."


@pytest.mark.asyncio
async def test_extraction_disabled_setting_skips_extractor(
    async_db_session: AsyncSession, embedding_provider
):
    """Verify setting memory_extraction_enabled=False skips calling the extractor."""
    provider = ScriptableMockProvider()
    extractor = MemoryExtractor(provider=provider)
    mem_service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    agent = KairoAgent(
        provider=provider,
        conversation_repo=ConversationRepository(async_db_session),
        memory_service=mem_service,
        memory_extractor=extractor,
        memory_extraction_enabled=False,  # Disabled
    )

    await agent.process_message("I am building Kairo.", session_id="sess_disabled")
    # Extractor call count must remain 0
    assert provider.extraction_call_count == 0
    mems = await mem_service.list_memories()
    assert len(mems) == 0


@pytest.mark.asyncio
async def test_tool_execution_works_with_memory_extraction(async_db_session: AsyncSession):
    """Verify tool execution loop completes normally alongside memory extraction."""
    tool_reg = ToolRegistry()
    tool_reg.register(CalculatorTool())
    tool_exec = ToolExecutor(registry=tool_reg)

    class ToolThenExtractionProvider(ModelProvider):
        def __init__(self):
            self.step = 0

        async def generate_response(self, messages, model=None, tools=None, **kwargs):
            is_extraction = any("Kairo's Memory Extractor" in str(m.content) for m in messages)
            if is_extraction:
                return ProviderResponse(content='{"candidates": []}')

            if self.step == 0:
                self.step += 1
                return ProviderResponse(
                    tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expression": "25 * 4"})]
                )
            return ProviderResponse(content="25 * 4 is 100.", model=model)

        async def stream_response(self, messages, model=None, tools=None, **kwargs):
            yield "25 * 4 is 100."

    provider = ToolThenExtractionProvider()
    extractor = MemoryExtractor(provider=provider)
    conv_repo = ConversationRepository(async_db_session)

    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
        tool_registry=tool_reg,
        tool_executor=tool_exec,
        memory_extractor=extractor,
        memory_extraction_enabled=True,
    )

    resp = await agent.process_message("What is 25 * 4?", session_id="sess_tool_extract")
    assert resp.message == "25 * 4 is 100."
    assert len(resp.tools_used) == 1
    assert resp.tools_used[0].tool == "calculator"
