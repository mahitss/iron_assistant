"""Unit tests for BrowserSession and BrowserManager lifecycle and session isolation."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.tools.browser.manager import BrowserManager


@pytest.mark.asyncio
async def test_session_lifecycle():
    """Test BrowserSession touch, expiration calculation, and close."""
    settings = Settings(
        KAIRO_BROWSER_ENABLED=True,
        KAIRO_BROWSER_HEADLESS=True,
        KAIRO_BROWSER_MAX_SESSIONS=3,
        KAIRO_BROWSER_SESSION_TIMEOUT_SECONDS=60,
    )
    manager = BrowserManager(settings=settings)
    try:
        session = await manager.get_or_create_session("sess_test_1")
        assert session.session_id == "sess_test_1"
        assert session.status == "active"
        assert session.context is not None
        assert session.page is not None

        # Touch updates last_used_at
        old_time = session.last_used_at
        session.touch()
        assert session.last_used_at >= old_time

        # Expiration logic
        assert not session.is_expired(timeout_seconds=60)
        session.last_used_at = datetime.now(UTC) - timedelta(seconds=120)
        assert session.is_expired(timeout_seconds=60)

        # Close session
        closed = await manager.close_session("sess_test_1")
        assert closed is True
        assert session.status == "closed"
        assert manager.get_session("sess_test_1") is None
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_browser_context_isolation():
    """Verify that two distinct sessions receive completely isolated browser contexts."""
    settings = Settings(KAIRO_BROWSER_ENABLED=True, KAIRO_BROWSER_HEADLESS=True)
    manager = BrowserManager(settings=settings)
    try:
        session_a = await manager.get_or_create_session("user_a")
        session_b = await manager.get_or_create_session("user_b")

        assert session_a.session_id != session_b.session_id
        assert session_a.context is not session_b.context
        assert session_a.page is not session_b.page
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_manager_max_sessions_eviction():
    """Verify that BrowserManager evicts the oldest session when max_sessions is exceeded."""
    settings = Settings(
        KAIRO_BROWSER_ENABLED=True,
        KAIRO_BROWSER_HEADLESS=True,
        KAIRO_BROWSER_MAX_SESSIONS=2,
    )
    manager = BrowserManager(settings=settings)
    try:
        sess1 = await manager.get_or_create_session("s1")
        # Ensure s1 is older
        sess1.last_used_at = datetime.now(UTC) - timedelta(seconds=30)

        await manager.get_or_create_session("s2")
        assert len(manager._sessions) == 2

        # Creating third session should evict s1 (the oldest)
        await manager.get_or_create_session("s3")
        assert len(manager._sessions) == 2

        assert "s1" not in manager._sessions
        assert "s2" in manager._sessions
        assert "s3" in manager._sessions
    finally:
        await manager.close_all()


@pytest.mark.asyncio
async def test_stale_session_cleanup():
    """Verify cleanup_stale_sessions removes expired sessions."""
    settings = Settings(
        KAIRO_BROWSER_ENABLED=True,
        KAIRO_BROWSER_HEADLESS=True,
        KAIRO_BROWSER_SESSION_TIMEOUT_SECONDS=10,
    )
    manager = BrowserManager(settings=settings)
    try:
        sess = await manager.get_or_create_session("stale_test")
        sess.last_used_at = datetime.now(UTC) - timedelta(seconds=20)

        cleaned = await manager.cleanup_stale_sessions()
        assert cleaned == 1
        assert manager.get_session("stale_test") is None
    finally:
        await manager.close_all()
