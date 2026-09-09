"""Tests for distributed locking, mandatory TTL, and fencing tokens (Task 39)."""

import pytest

from app.state.locks import (
    LockAcquisitionError,
    StaleFencingTokenError,
    state_lock_manager,
)


@pytest.fixture(autouse=True)
def clean_locks():
    state_lock_manager.clear()
    yield
    state_lock_manager.clear()


@pytest.mark.asyncio
async def test_lock_acquisition_and_fencing_token():
    """Acquiring a lock returns a strictly increasing fencing token."""
    token1 = await state_lock_manager.acquire_lock("resource_key_1", "worker_a", ttl_seconds=10.0)
    assert token1 == 1

    # Same worker re-acquiring or next lease gets higher token
    await state_lock_manager.release_lock("resource_key_1", "worker_a")
    token2 = await state_lock_manager.acquire_lock("resource_key_1", "worker_b", ttl_seconds=10.0)
    assert token2 == 2


@pytest.mark.asyncio
async def test_lock_contention_rejected():
    """Lock held by worker A cannot be acquired by worker B before expiry."""
    await state_lock_manager.acquire_lock("resource_contended", "worker_a", ttl_seconds=10.0)

    with pytest.raises(LockAcquisitionError) as exc_info:
        await state_lock_manager.acquire_lock("resource_contended", "worker_b", ttl_seconds=10.0)
    assert "already held by worker 'worker_a'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stale_fencing_token_rejected():
    """Worker presenting an old fencing token is rejected with StaleFencingTokenError."""
    # Worker A gets token 1
    token_a = await state_lock_manager.acquire_lock("resource_fenced", "worker_a")
    assert token_a == 1

    # Worker A loses lease; Worker B gets token 2
    await state_lock_manager.release_lock("resource_fenced", "worker_a")
    token_b = await state_lock_manager.acquire_lock("resource_fenced", "worker_b")
    assert token_b == 2

    # Worker A attempts to commit with stale token 1
    with pytest.raises(StaleFencingTokenError) as exc_info:
        await state_lock_manager.verify_fencing_token("resource_fenced", token_a)
    assert "Fencing token 1 on key 'resource_fenced' is stale!" in str(exc_info.value)
