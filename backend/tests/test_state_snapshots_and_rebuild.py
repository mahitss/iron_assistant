"""Tests for snapshot integrity, corruption defense, and side-effect-free rebuilds (Task 39)."""

import pytest

from app.state.rebuild import rebuild_coordinator
from app.state.snapshots import snapshot_manager


@pytest.fixture(autouse=True)
def clean_snapshots():
    snapshot_manager.clear()
    rebuild_coordinator.clear()
    yield
    snapshot_manager.clear()
    rebuild_coordinator.clear()


def test_snapshot_deterministic_checksum_and_load():
    """Valid snapshot loads correctly when checksum matches."""
    payload = {"entities": [{"id": "e1", "name": "Device A"}], "status": "READY"}
    snp = snapshot_manager.create_snapshot(
        projection_identifier="world_model_projection",
        state_version=10,
        payload=payload,
        schema_version=1,
    )
    assert snp.checksum is not None

    loaded = snapshot_manager.load_latest_valid_snapshot(
        projection_identifier="world_model_projection",
        required_schema_version=1,
    )
    assert loaded is not None
    assert loaded.id == snp.id
    assert loaded.state_version == 10


def test_corrupt_snapshot_rejected_and_fallback_to_previous():
    """Corrupted snapshot is rejected and system safely falls back to previous valid snapshot."""
    # 1. Valid previous snapshot v1
    payload_v1 = {"step": 1}
    snp_v1 = snapshot_manager.create_snapshot("proj_fallback", 1, payload_v1)

    # 2. Corrupt snapshot v2 (simulate tampering or disk corruption)
    snp_v2 = snapshot_manager.create_snapshot("proj_fallback", 2, {"step": 2})
    snp_v2.checksum = "corrupted_bad_hash_999999"

    # 3. Loading should skip v2 and return valid v1
    loaded = snapshot_manager.load_latest_valid_snapshot("proj_fallback")
    assert loaded is not None
    assert loaded.id == snp_v1.id
    assert loaded.state_version == 1


@pytest.mark.asyncio
async def test_side_effect_free_projection_rebuild():
    """Projection rebuild runs without triggering side effects and uses blue/green atomic swap."""
    mock_source = [
        {"id": "rec_1", "raw_data": "item A"},
        {"id": "rec_2", "raw_data": "item B"},
    ]

    def source_fetcher():
        return mock_source

    def projection_mapper(record):
        # Invariant: No external side effects during rebuild
        assert rebuild_coordinator.side_effects_blocked is True
        return {"id": record["id"], "mapped": record["raw_data"].upper()}

    result = await rebuild_coordinator.rebuild_projection(
        projection_id="test_projection",
        authoritative_source_fetcher=source_fetcher,
        projection_mapper=projection_mapper,
    )

    assert result["record_count"] == 2
    assert result["items"]["rec_1"]["mapped"] == "ITEM A"
    assert result["items"]["rec_2"]["mapped"] == "ITEM B"
    assert rebuild_coordinator.is_rebuilding is False
    assert rebuild_coordinator.side_effects_blocked is False
