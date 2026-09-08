"""Unit tests for KairoAgent memory integration: conversation history, semantic memories, and tools."""

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.core import KairoAgent
from app.db.session import Base
from app.memory.embeddings import DeterministicEmbeddingProvider
from app.memory.repository import ConversationRepository
from app.memory.schemas import MemoryType
from app.memory.service import MemoryService
from app.memory.session import SessionManager
from app.models.provider import (
    ChatMessage,
    MessageRole,
    ModelProvider,
    ProviderAPIError,
    ProviderResponse,
)
from app.tools.executor import ToolExecutor


class RecordingMockProvider(ModelProvider):
    """Mock provider that records the exact prompt messages passed to it."""

    def __init__(self, responses: list[str] | None = None):
        self.recorded_messages: list[list[ChatMessage]] = []
        self.responses = responses or ["Hello from Kairo!"]
        self._call_count = 0
        self.fail_on_next_call = False

    async def generate_response(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        **kwargs,
    ) -> ProviderResponse:
        self.recorded_messages.append(list(messages))
        if self.fail_on_next_call:
            raise ProviderAPIError("Simulated upstream provider outage", status_code=502)

        resp_text = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        return ProviderResponse(
            content=resp_text,
            model=model,
            prompt_tokens=10,
            completion_tokens=10,
            total_tokens=20,
        )

    async def stream_response(
        self,
        messages: list[ChatMessage],
        model: str,
        tools: list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        self.recorded_messages.append(list(messages))
        if self.fail_on_next_call:
            raise ProviderAPIError("Simulated upstream stream outage", status_code=502)
        resp_text = self.responses[self._call_count % len(self.responses)]
        self._call_count += 1
        for word in resp_text.split(" "):
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


@pytest.mark.asyncio
async def test_agent_generates_session_id_when_omitted(async_db_session: AsyncSession):
    """Verify that omitting session_id causes KairoAgent to generate one."""
    provider = RecordingMockProvider(["I am Kairo."])
    agent = KairoAgent(
        provider=provider,
        conversation_repo=ConversationRepository(async_db_session),
        session_manager=SessionManager(),
    )

    response = await agent.process_message("Hello!")
    assert response.session_id is not None
    assert response.session_id.startswith("sess_")
    assert response.message == "I am Kairo."


@pytest.mark.asyncio
async def test_conversation_history_reaches_model(async_db_session: AsyncSession):
    """Verify that subsequent messages in the same session include previous turns."""
    provider = RecordingMockProvider(
        [
            "Nice to meet you Alice.",
            "Your name is Alice.",
        ]
    )
    conv_repo = ConversationRepository(async_db_session)
    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
        session_manager=SessionManager(),
    )

    session_id = "sess_test_memory_continuity"

    # First turn
    resp1 = await agent.process_message("My name is Alice.", session_id=session_id)
    assert resp1.session_id == session_id
    assert resp1.message == "Nice to meet you Alice."

    # Second turn
    resp2 = await agent.process_message("What is my name?", session_id=session_id)
    assert resp2.session_id == session_id

    # Inspect second turn prompt messages sent to provider
    second_turn_messages = provider.recorded_messages[1]
    roles = [m.role for m in second_turn_messages]
    contents = [m.content for m in second_turn_messages]

    # Should contain System, User ("My name is Alice."), Assistant ("Nice to meet you Alice."), User ("What is my name?")
    assert MessageRole.SYSTEM in roles
    assert "My name is Alice." in contents
    assert "Nice to meet you Alice." in contents
    assert "What is my name?" in contents


@pytest.mark.asyncio
async def test_relevant_memories_reach_model_context(async_db_session: AsyncSession):
    """Verify relevant persistent memories are injected into model prompt."""
    embedding_provider = DeterministicEmbeddingProvider(dimension=64)
    mem_service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    # Store a preference memory
    await mem_service.create_memory(
        content="User prefers Python for data analysis.",
        memory_type=MemoryType.PREFERENCE,
        importance=0.9,
    )

    provider = RecordingMockProvider(["Python is great for data analysis!"])
    agent = KairoAgent(
        provider=provider,
        conversation_repo=ConversationRepository(async_db_session),
        memory_service=mem_service,
        embedding_provider=embedding_provider,
    )

    await agent.process_message("What language should I use for data analysis?", session_id="sess_pref")

    first_turn_messages = provider.recorded_messages[0]
    system_message = next(m for m in first_turn_messages if m.role == MessageRole.SYSTEM)

    # Memory content must be present in the system prompt context
    assert "Relevant memories:" in system_message.content
    assert "User prefers Python for data analysis." in system_message.content


@pytest.mark.asyncio
async def test_irrelevant_memories_not_injected(async_db_session: AsyncSession):
    """Verify that when no relevant memories match, no memory header is injected into prompt."""
    embedding_provider = DeterministicEmbeddingProvider(dimension=64)
    # Empty memory store
    mem_service = MemoryService(session=async_db_session, embedding_provider=embedding_provider)

    provider = RecordingMockProvider(["General response"])
    agent = KairoAgent(
        provider=provider,
        conversation_repo=ConversationRepository(async_db_session),
        memory_service=mem_service,
        embedding_provider=embedding_provider,
    )

    await agent.process_message("Hello Kairo, how are you?", session_id="sess_empty_mem")
    first_turn_messages = provider.recorded_messages[0]
    system_message = next(m for m in first_turn_messages if m.role == MessageRole.SYSTEM)

    assert "Relevant memories:" not in system_message.content


@pytest.mark.asyncio
async def test_assistant_response_persisted_in_db(async_db_session: AsyncSession):
    """Verify that successful assistant messages are committed to the DB history."""
    conv_repo = ConversationRepository(async_db_session)
    provider = RecordingMockProvider(["Stored assistant answer."])
    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
        session_manager=SessionManager(),
    )

    session_id = "sess_persistence_check"
    await agent.process_message("Save this test.", session_id=session_id)

    conv = await conv_repo.get_by_session_id(session_id)
    assert conv is not None
    messages = await conv_repo.get_recent_messages(conv.id, limit=10)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Save this test."
    assert messages[1].role == "assistant"
    assert messages[1].content == "Stored assistant answer."


@pytest.mark.asyncio
async def test_failed_model_calls_do_not_persist_assistant_message(async_db_session: AsyncSession):
    """Verify that exceptions during generation do not leave partial/misleading assistant messages."""
    conv_repo = ConversationRepository(async_db_session)
    provider = RecordingMockProvider()
    provider.fail_on_next_call = True

    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
    )

    session_id = "sess_failure_check"
    with pytest.raises(ProviderAPIError):
        await agent.process_message("Will fail", session_id=session_id)

    conv = await conv_repo.get_by_session_id(session_id)
    assert conv is not None
    messages = await conv_repo.get_recent_messages(conv.id, limit=10)
    # Only the user message was recorded; no assistant message was saved
    assert len(messages) == 1
    assert messages[0].role == "user"


@pytest.mark.asyncio
async def test_bounded_conversation_history(async_db_session: AsyncSession):
    """Verify that conversation history sent to the model does not exceed max_context_messages."""
    conv_repo = ConversationRepository(async_db_session)
    provider = RecordingMockProvider(["Acknowledged."])
    max_msgs = 4
    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
        max_context_messages=max_msgs,
    )

    session_id = "sess_bounded"
    # Send 5 turns (10 messages total: 5 user, 5 assistant)
    for i in range(5):
        await agent.process_message(f"Message {i}", session_id=session_id)

    last_call_messages = provider.recorded_messages[-1]
    # Non-system messages should not exceed max_msgs (4)
    non_system = [m for m in last_call_messages if m.role != MessageRole.SYSTEM]
    assert len(non_system) <= max_msgs


@pytest.mark.asyncio
async def test_tools_work_with_memory_and_history(async_db_session: AsyncSession):
    """Verify tool execution loop functions seamlessly alongside memory and conversation history."""
    from app.tools.builtin.calculator import CalculatorTool
    from app.tools.registry import ToolRegistry
    from app.tools.schemas import ToolCall

    tool_reg = ToolRegistry()
    tool_reg.register(CalculatorTool())
    tool_exec = ToolExecutor(registry=tool_reg)

    class ToolThenAnswerProvider(ModelProvider):
        def __init__(self):
            self.step = 0
            self.recorded = []

        async def generate_response(self, messages, model, tools=None, **kwargs):
            self.recorded.append(list(messages))
            if self.step == 0:
                self.step += 1
                return ProviderResponse(
                    tool_calls=[ToolCall(id="c1", name="calculator", arguments={"expression": "12 * 12"})]
                )
            return ProviderResponse(content="12 * 12 is 144.", model=model)

        async def stream_response(self, messages, model, tools=None, **kwargs):
            yield "12 * 12 is 144."

    conv_repo = ConversationRepository(async_db_session)
    provider = ToolThenAnswerProvider()
    agent = KairoAgent(
        provider=provider,
        conversation_repo=conv_repo,
        tool_registry=tool_reg,
        tool_executor=tool_exec,
    )

    session_id = "sess_tool_memory"
    res = await agent.process_message("Compute 12 * 12", session_id=session_id)
    assert res.message == "12 * 12 is 144."
    assert len(res.tools_used) == 1
    assert res.tools_used[0].tool == "calculator"
    assert res.tools_used[0].status == "success"

    # Verify conversation history in DB has user and final assistant response
    conv = await conv_repo.get_by_session_id(session_id)
    assert conv is not None
    messages = await conv_repo.get_recent_messages(conv.id, limit=10)
    assert len(messages) >= 2
    assert messages[0].role == "user"
    assert messages[-1].role == "assistant"
    assert messages[-1].content == "12 * 12 is 144."
