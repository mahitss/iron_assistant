"""Tests for Kairo standalone worker and scheduler execution loop."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.worker import KairoWorker


@pytest.mark.asyncio
async def test_worker_initialization():
    """Verify worker initializes with configured intervals and stop event unset."""
    worker = KairoWorker(poll_interval_seconds=2.0, stale_recovery_interval_seconds=60.0)
    assert worker.poll_interval_seconds == 2.0
    assert worker.stale_recovery_interval_seconds == 60.0
    assert not worker._stop_event.is_set()


@pytest.mark.asyncio
async def test_worker_run_once_empty(monkeypatch):
    """Verify worker poll cycle returns 0 when no due workflows exist."""
    worker = KairoWorker()

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    # Mock poll_due_workflows returning empty list
    monkeypatch.setattr(
        "app.worker.SchedulerService.poll_due_workflows",
        AsyncMock(return_value=[]),
    )

    processed = await worker.run_once(mock_session_factory)
    assert processed == 0


@pytest.mark.asyncio
async def test_worker_run_once_executes_claimed_runs(monkeypatch):
    """Verify worker executes runs claimed by the scheduler."""
    worker = KairoWorker()

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    # Mock scheduler returning 2 claimed run IDs
    claimed_ids = ["run-1", "run-2"]
    monkeypatch.setattr(
        "app.worker.SchedulerService.poll_due_workflows",
        AsyncMock(return_value=claimed_ids),
    )

    # Mock workflow executor
    mock_execute = AsyncMock(return_value=MagicMock())
    monkeypatch.setattr("app.worker.WorkflowExecutor.execute_run", mock_execute)

    processed = await worker.run_once(mock_session_factory)
    assert processed == 2
    assert mock_execute.call_count == 2
    mock_execute.assert_any_call("run-1")
    mock_execute.assert_any_call("run-2")


@pytest.mark.asyncio
async def test_worker_recover_stale(monkeypatch):
    """Verify worker triggers stale run recovery."""
    worker = KairoWorker()

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session
    mock_session_factory.return_value.__aexit__.return_value = None

    mock_recover = AsyncMock(return_value=3)
    monkeypatch.setattr("app.worker.SchedulerService.recover_stale_runs", mock_recover)

    recovered = await worker.recover_stale(mock_session_factory)
    assert recovered == 3


def test_worker_stop_signal():
    """Verify stopping worker sets the stop event."""
    worker = KairoWorker()
    assert not worker._stop_event.is_set()
    worker.stop()
    assert worker._stop_event.is_set()
