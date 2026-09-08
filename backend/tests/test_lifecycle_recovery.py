"""Tests for application startup recovery of stale workflows/tasks and shutdown cleanup."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.lifecycle import shutdown_lifecycle, startup_lifecycle


@pytest.mark.asyncio
async def test_startup_lifecycle_resets_computer_control(monkeypatch):
    """Startup lifecycle validates environment and ensures computer control starts disabled."""
    from app.config.settings import get_settings

    cfg = get_settings()
    cfg.KAIRO_COMPUTER_ENABLED = True

    await startup_lifecycle()

    # Must be disabled after startup
    assert cfg.KAIRO_COMPUTER_ENABLED is False


@pytest.mark.asyncio
async def test_startup_lifecycle_recovers_stale_records(monkeypatch):
    """Startup recovers stale RUNNING and PENDING tasks from the database."""
    mock_session = AsyncMock()
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__.return_value = mock_session

    from app.config.settings import get_settings

    cfg = get_settings()
    monkeypatch.setattr(cfg, "DATABASE_URL", "postgresql+asyncpg://mock:mock@localhost/db")
    monkeypatch.setattr("app.lifecycle.get_sessionmaker", lambda: mock_factory)

    await startup_lifecycle()

    # Verify SQL updates for workflow_runs and agent_tasks were executed
    assert mock_session.execute.call_count >= 2
    assert mock_session.commit.call_count >= 1


@pytest.mark.asyncio
async def test_shutdown_lifecycle_closes_resources(monkeypatch):
    """Shutdown lifecycle closes browser manager, voice sessions, and database connections."""
    mock_manager = AsyncMock()
    monkeypatch.setattr("app.tools.browser.manager.get_browser_manager", lambda: mock_manager)

    mock_engine = AsyncMock()
    monkeypatch.setattr("app.lifecycle.get_engine", lambda: mock_engine)

    await shutdown_lifecycle()

    assert mock_manager.close_all.call_count == 1
    assert mock_engine.dispose.call_count == 1
