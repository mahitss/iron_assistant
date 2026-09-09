"""Tests for data integrity scanning and quarantine isolation (Task 39)."""

import pytest

from app.state.fabric import state_fabric
from app.state.integrity import StateIntegrityScanner
from app.state.quarantine import state_quarantine
from app.state.schemas import StateDomain, StateRecord


@pytest.fixture(autouse=True)
def clean_state():
    state_fabric.clear()
    state_quarantine.clear()
    yield
    state_fabric.clear()
    state_quarantine.clear()


def test_integrity_scanner_impossible_state():
    """Detects impossible state: COMPLETED task holding an active execution lease."""
    impossible_record = StateRecord(
        id="rec_bad",
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_bad",
        version=1,
        status="COMPLETED",
        data={"lease_owner": "worker_zombie", "lease_expires_at": 9999999999},
        checksum="abcdef1234567890abcdef1234567890",
        owner_domain=StateDomain.TASKS,
    )

    violations = StateIntegrityScanner.scan_record(impossible_record)
    assert len(violations) == 1
    assert violations[0].violation_type == "IMPOSSIBLE_STATE"
    assert "active execution lease" in violations[0].description


@pytest.mark.asyncio
async def test_quarantined_record_mutation_blocked():
    """Quarantined resource cannot be mutated by any service."""
    # 1. Quarantine resource
    state_quarantine.quarantine(
        resource_type="task",
        resource_id="task_poison",
        reason="Corrupt state detected",
    )
    assert state_quarantine.is_quarantined("task_poison") is True

    # 2. Attempting to create or mutate in state_fabric must be rejected
    with pytest.raises(PermissionError) as exc_info:
        await state_fabric.create_record(
            domain=StateDomain.TASKS,
            resource_type="task",
            resource_id="task_poison",
            data={"val": 1},
            calling_service="task_engine",
        )
    assert "currently quarantined" in str(exc_info.value)

    # 3. Release by operator
    released = state_quarantine.release("task_poison", released_by="admin_alice")
    assert released is True
    assert state_quarantine.is_quarantined("task_poison") is False
