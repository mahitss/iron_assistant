"""Unit tests for conversation, message, and memory repositories."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.memory.repository import (
    ConversationRepository,
    MemoryRepository,
    cosine_similarity,
)


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


def test_cosine_similarity():
    """Verify vector cosine similarity calculation in Python fallback."""
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == pytest.approx(1.0)

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == pytest.approx(0.0)

    # Empty or mismatched vectors
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([1.0], [1.0, 2.0]) == 0.0


@pytest.mark.asyncio
async def test_conversation_creation_and_lookup(async_db_session: AsyncSession):
    """Test creating and finding conversations by session_id."""
    repo = ConversationRepository(async_db_session)

    # Create new conversation
    conv1 = await repo.get_or_create("sess_test_123")
    assert conv1.id is not None
    assert conv1.session_id == "sess_test_123"

    # Lookup existing conversation
    conv2 = await repo.get_or_create("sess_test_123")
    assert conv2.id == conv1.id

    # Lookup by session_id
    found = await repo.get_by_session_id("sess_test_123")
    assert found is not None
    assert found.id == conv1.id


@pytest.mark.asyncio
async def test_message_creation_and_bounded_history(async_db_session: AsyncSession):
    """Test adding messages and retrieving chronological bounded history."""
    conv_repo = ConversationRepository(async_db_session)
    conv = await conv_repo.get_or_create("sess_msgs_test")

    # Add messages
    m1 = await conv_repo.add_message(conv.id, role="user", content="Hello")
    m2 = await conv_repo.add_message(conv.id, role="assistant", content="Hi there!")
    m3 = await conv_repo.add_message(conv.id, role="user", content="How are you?")

    assert m1.id is not None
    assert m2.role == "assistant"
    assert m3.content == "How are you?"

    # Retrieve all recent messages (limit 10)
    messages = await conv_repo.get_recent_messages(conv.id, limit=10)
    assert len(messages) == 3
    assert [m.role for m in messages] == ["user", "assistant", "user"]
    assert [m.content for m in messages] == ["Hello", "Hi there!", "How are you?"]

    # Verify bounded history limit (limit 2)
    bounded = await conv_repo.get_recent_messages(conv.id, limit=2)
    assert len(bounded) == 2
    # Chronological order of the last 2 messages
    assert bounded[0].content == "Hi there!"
    assert bounded[1].content == "How are you?"


@pytest.mark.asyncio
async def test_memory_crud_operations(async_db_session: AsyncSession):
    """Test memory creation, retrieval, update, and deletion."""
    repo = MemoryRepository(async_db_session)

    # 1. Create memory
    mem = await repo.create(
        content="User prefers Python over Java",
        memory_type="preference",
        embedding=[0.5, 0.5, 0.0],
        importance=0.8,
        source="explicit",
    )
    assert mem.id is not None
    assert mem.content == "User prefers Python over Java"
    assert mem.memory_type == "preference"
    assert mem.importance == 0.8

    # 2. Get by ID
    fetched = await repo.get_by_id(mem.id)
    assert fetched is not None
    assert fetched.id == mem.id

    # 3. Update memory
    updated = await repo.update(
        memory=fetched,
        content="User strongly prefers Python over Java",
        importance=0.9,
    )
    assert updated.content == "User strongly prefers Python over Java"
    assert updated.importance == 0.9

    # 4. Search similar (Python fallback in SQLite)
    results = await repo.search_similar(query_embedding=[0.5, 0.5, 0.0], top_k=5)
    assert len(results) == 1
    result_mem, similarity = results[0]
    assert result_mem.id == mem.id
    assert similarity == pytest.approx(1.0)

    # 5. Delete memory
    deleted = await repo.delete(mem.id)
    assert deleted is True

    # 6. Verify deletion
    after_delete = await repo.get_by_id(mem.id)
    assert after_delete is None
