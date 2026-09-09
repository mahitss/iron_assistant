"""Tests for domain ownership matrix, boundaries, and security scoping (Task 39)."""

import pytest

from app.state.fabric import state_fabric
from app.state.ownership import DomainOwnershipRegistry
from app.state.schemas import StateClassification, StateDomain


@pytest.fixture(autouse=True)
def clean_state():
    state_fabric.clear()
    yield
    state_fabric.clear()


@pytest.mark.asyncio
async def test_domain_ownership_authorized_mutation():
    """Authorized service can mutate authoritative domain state."""
    record = await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_123",
        data={"name": "Test Task", "status": "PENDING"},
        calling_service="task_engine",
        user_id="user_1",
    )
    assert record.resource_id == "task_123"
    assert record.version == 1
    assert record.classification == StateClassification.AUTHORITATIVE


@pytest.mark.asyncio
async def test_domain_ownership_unauthorized_mutation_rejected():
    """Service unauthorized for a domain is rejected with PermissionError."""
    with pytest.raises(PermissionError) as exc_info:
        await state_fabric.create_record(
            domain=StateDomain.POLICIES,
            resource_type="policy",
            resource_id="pol_456",
            data={"rules": []},
            calling_service="memory_service",  # Unauthorized!
            user_id="user_1",
        )
    assert "not authorized to mutate authoritative state for domain 'policies'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cross_user_isolation_denied():
    """User B cannot access or mutate records owned by User A."""
    await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_user_a",
        data={"secret": "user A data"},
        calling_service="task_engine",
        user_id="user_a",
    )

    with pytest.raises(PermissionError) as exc_info:
        await state_fabric.get_record(
            domain=StateDomain.TASKS,
            resource_type="task",
            resource_id="task_user_a",
            request_user_id="user_b",  # Different user!
        )
    assert "Cross-user state access denied" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cross_project_isolation_denied():
    """Project Y cannot access records belonging to Project X."""
    await state_fabric.create_record(
        domain=StateDomain.PROJECTS,
        resource_type="project_spec",
        resource_id="spec_proj_x",
        data={"config": "prod"},
        calling_service="project_service",
        project_id="proj_x",
    )

    with pytest.raises(PermissionError) as exc_info:
        await state_fabric.get_record(
            domain=StateDomain.PROJECTS,
            resource_type="project_spec",
            resource_id="spec_proj_x",
            request_project_id="proj_y",  # Different project!
        )
    assert "Cross-project state access denied" in str(exc_info.value)


@pytest.mark.asyncio
async def test_derived_state_bypasses_authoritative_mutation_lock():
    """Derived projections can be updated by projection services without authoritative ownership errors."""
    record = await state_fabric.create_record(
        domain=StateDomain.WORLD,
        resource_type="world_entity",
        resource_id="ent_789",
        data={"type": "device_summary"},
        calling_service="projection_builder",
        classification=StateClassification.DERIVED,
    )
    assert record.classification == StateClassification.DERIVED
