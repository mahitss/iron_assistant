"""Tests for durable changelog engine and credential scrubbing (Task 39)."""

import pytest

from app.state.changelog import state_changelog
from app.state.fabric import state_fabric
from app.state.schemas import OperationType, StateDomain


@pytest.fixture(autouse=True)
def clean_state():
    state_fabric.clear()
    state_changelog.clear()
    yield
    state_fabric.clear()
    state_changelog.clear()


@pytest.mark.asyncio
async def test_changelog_records_mutations_with_actors():
    """Mutations append entries to the changelog with actor, service, and correlation ID."""
    await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="task_audit_1",
        data={"action": "deploy"},
        calling_service="task_engine",
        actor="alice",
        correlation_id="corr_999",
    )

    history = state_changelog.get_history(resource_type="task", resource_id="task_audit_1")
    assert len(history) == 1
    assert history[0].operation == OperationType.CREATE
    assert history[0].actor == "alice"
    assert history[0].service == "task_engine"
    assert history[0].correlation_id == "corr_999"


def test_changelog_secret_scrubbing():
    """Secrets, API keys, and Bearer tokens are scrubbed from changelog diffs."""
    raw_changes = {
        "api_key": "sk-ant-live-secret-key-12345",
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.token",
        "normal_field": "public_value",
    }

    entry = state_changelog.record_change(
        domain=StateDomain.POLICIES,
        resource_type="secret_policy",
        resource_id="sec_pol_1",
        version=1,
        operation=OperationType.UPDATE,
        actor="operator",
        service="policy_engine",
        changes=raw_changes,
    )

    assert entry.changes is not None
    assert entry.changes["api_key"] == "[REDACTED]"
    assert entry.changes["authorization"] == "[REDACTED]"
    assert entry.changes["normal_field"] == "public_value"
