"""Tests for monotonic versioning and optimistic concurrency control (Task 39)."""

import pytest

from app.state.fabric import state_fabric
from app.state.schemas import StateDomain
from app.state.versions import StateConflictError, VersionManager


@pytest.fixture(autouse=True)
def clean_state():
    state_fabric.clear()
    yield
    state_fabric.clear()


@pytest.mark.asyncio
async def test_monotonic_version_increment():
    """Each update strictly increments version by 1."""
    rec = await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_version_test",
        data={"step": 1},
        calling_service="task_engine",
    )
    assert rec.version == 1

    updated_1 = await state_fabric.update_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_version_test",
        new_data={"step": 2},
        expected_version=1,
        calling_service="task_engine",
    )
    assert updated_1.version == 2

    updated_2 = await state_fabric.update_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_version_test",
        new_data={"step": 3},
        expected_version=2,
        calling_service="task_engine",
    )
    assert updated_2.version == 3


@pytest.mark.asyncio
async def test_optimistic_concurrency_lost_update_prevention():
    """Updating with a stale expected version raises StateConflictError."""
    await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_race_condition",
        data={"counter": 10},
        calling_service="task_engine",
    )

    # Worker 1 updates from v1 to v2
    await state_fabric.update_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_race_condition",
        new_data={"counter": 11},
        expected_version=1,
        calling_service="task_engine",
    )

    # Worker 2 attempts update with stale v1
    with pytest.raises(StateConflictError) as exc_info:
        await state_fabric.update_record(
            domain=StateDomain.TASKS,
            resource_type="task",
            resource_id="task_race_condition",
            new_data={"counter": 99},
            expected_version=1,  # Stale version!
            calling_service="task_engine",
        )
    assert "expected version 1, but actual version is 2" in str(exc_info.value)


def test_client_version_forgery_protection():
    """Clients cannot forge arbitrary future versions."""
    with pytest.raises(ValueError) as exc_info:
        VersionManager.validate_client_version(client_version=999, authoritative_version=5)
    assert "Client version forgery detected" in str(exc_info.value)
