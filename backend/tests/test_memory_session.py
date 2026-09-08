"""Unit tests for SessionManager and ephemeral session caching with Redis/fallback."""

import pytest

from app.memory.session import SessionManager


@pytest.mark.asyncio
async def test_session_manager_in_memory_fallback():
    """Verify session manager works seamlessly when Redis URL is None or Redis is unreachable."""
    manager = SessionManager(redis_url=None, default_ttl=3600)

    # Initial get returns None
    state = await manager.get_session_state("sess_123")
    assert state is None

    # Set session state
    test_state = {"last_model": "test/model", "turn_count": 1}
    await manager.set_session_state("sess_123", test_state)

    # Retrieve session state
    retrieved = await manager.get_session_state("sess_123")
    assert retrieved == test_state

    # Clear session state
    await manager.clear_session_state("sess_123")
    cleared = await manager.get_session_state("sess_123")
    assert cleared is None


@pytest.mark.asyncio
async def test_session_manager_graceful_redis_failure():
    """Verify session manager catches Redis errors and falls back to in-memory without raising."""
    # Point to an invalid unreachable Redis host
    manager = SessionManager(redis_url="redis://127.0.0.1:19999/0", default_ttl=60)

    test_state = {"active": True}
    # Setting and getting should gracefully fall back to in-memory store
    await manager.set_session_state("sess_failover", test_state)
    retrieved = await manager.get_session_state("sess_failover")
    assert retrieved == test_state

    await manager.close()
