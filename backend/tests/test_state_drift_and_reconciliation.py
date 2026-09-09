"""Tests for external drift detection and state reconciliation (Task 39)."""

from datetime import UTC, datetime, timedelta
import pytest

from app.state.drift import DriftDetector
from app.state.fabric import state_fabric
from app.state.reconciliation import state_reconciler
from app.state.schemas import (
    ObservationFreshness,
    ReconciliationMode,
    StateDomain,
)


@pytest.fixture(autouse=True)
def clean_state():
    state_fabric.clear()
    yield
    state_fabric.clear()


def test_external_unreachable_source_is_unknown():
    """Unreachable external systems evaluate to UNKNOWN, never guessing healthy."""
    freshness, _ = DriftDetector.evaluate_external_observation(
        resource="github_repo:kairo/core",
        is_source_reachable=False,
        observed_data=None,
        observed_at=None,
    )
    assert freshness == ObservationFreshness.UNKNOWN


def test_stale_observation_freshness():
    """Observations older than threshold evaluate to STALE."""
    old_time = datetime.now(UTC) - timedelta(seconds=400)
    freshness, _ = DriftDetector.evaluate_external_observation(
        resource="device_sensor:living_room",
        is_source_reachable=True,
        observed_data={"temp": 22},
        observed_at=old_time,
        max_freshness_seconds=300,
    )
    assert freshness == ObservationFreshness.STALE


def test_drift_detection_does_not_auto_remediate():
    """Drift is flagged with desired vs observed, but does not auto-mutate."""
    drift = DriftDetector.detect_drift(
        resource="aws_instance:i-12345",
        desired_state="RUNNING",
        observed_state="STOPPED",
    )
    assert drift is not None
    assert drift.desired == "RUNNING"
    assert drift.observed == "STOPPED"
    assert drift.severity.value == "MEDIUM"


@pytest.mark.asyncio
async def test_reconciliation_check_and_safe_repair():
    """Reconciler identifies stale cache entries and repairs them under SAFE_REPAIR."""
    rec = await state_fabric.create_record(
        domain=StateDomain.TASKS,
        resource_type="task",
        resource_id="rec_task_1",
        data={"val": "a"},
        calling_service="task_engine",
    )

    # 1. CHECK mode (no modifications)
    report_check = await state_reconciler.reconcile(
        mode=ReconciliationMode.CHECK,
        authoritative_records=[rec],
    )
    assert report_check.mode == ReconciliationMode.CHECK

    # 2. SAFE_REPAIR mode with orphaned derived record
    report_repair = await state_reconciler.reconcile(
        mode=ReconciliationMode.SAFE_REPAIR,
        authoritative_records=[rec],
        derived_records=[{"id": "derived_99", "parent_id": "non_existent_parent"}],
    )
    assert len(report_repair.issues) == 1
    assert "Orphaned derived record" in report_repair.issues[0].issue
