"""Tests for scoped state caching, stampede protection, and cache invalidation (Task 39)."""

import pytest

from app.state.cache import scoped_cache
from app.state.fabric import state_fabric
from app.state.invalidation import cache_invalidator
from app.state.schemas import StateDomain


@pytest.fixture(autouse=True)
def clean_cache():
    scoped_cache.clear()
    state_fabric.clear()
    yield
    scoped_cache.clear()
    state_fabric.clear()


def test_scoped_cache_key_generation():
    """Cache keys strictly include user and project scopes."""
    key = scoped_cache.build_scoped_key(
        domain="tasks",
        resource_id="task_123",
        user_id="alice",
        project_id="secret_project",
    )
    assert key == "tasks:task_123:u_alice:p_secret_project"


def test_versioned_cache_stale_detection():
    """Cache returns None if cached version is older than required version."""
    key = "tasks:task_ver"
    scoped_cache.put(key, value={"name": "test"}, version=1)

    # Required v1 succeeds
    assert scoped_cache.get(key, min_required_version=1) is not None

    # Required v2 evicts stale v1 and returns None
    assert scoped_cache.get(key, min_required_version=2) is None


@pytest.mark.asyncio
async def test_automatic_cache_invalidation_on_update():
    """Updating state automatically clears cached entries."""
    # 1. Create record (populates cache)
    await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_cached",
        data={"status": "INITIAL"},
        calling_service="task_engine",
        user_id="user_1",
    )
    cache_key = scoped_cache.build_scoped_key("tasks", "task_cached", user_id="user_1")
    assert scoped_cache.get(cache_key) is not None

    # 2. Update record
    await state_fabric.update_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_cached",
        new_data={"status": "UPDATED"},
        expected_version=1,
        calling_service="task_engine",
        request_user_id="user_1",
    )

    # 3. Cached entry must be invalidated
    assert scoped_cache.get(cache_key) is None


@pytest.mark.asyncio
async def test_cache_stampede_protection():
    """get_or_set_stampede_protected executes fetcher safely."""
    calls = 0

    def fetch_data():
        nonlocal calls
        calls += 1
        return {"data": "computed"}

    val1 = await scoped_cache.get_or_set_stampede_protected("test:stampede", fetch_data)
    val2 = await scoped_cache.get_or_set_stampede_protected("test:stampede", fetch_data)

    assert val1 == {"data": "computed"}
    assert val2 == {"data": "computed"}
    assert calls == 1  # Called only once!
