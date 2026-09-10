"""Unit tests for Safety Guards, Secret Protection, Isolation Boundaries, and Governance (Task 54)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.environment.authorization import EnvironmentAuthorizationEngine
from app.environment.cloud import CloudModelManager
from app.environment.databases import DatabaseContentIngestionError, DatabaseModelManager
from app.environment.digital_twin import DigitalTwinEngine
from app.environment.environments import EnvironmentManager
from app.environment.networks import NetworkModelManager
from app.environment.processes import ProcessModelManager
from app.environment.reconciliation import ReconciliationEngine
from app.environment.safety import (
    EnvironmentSafetyGuard,
    ProductionSafetyViolationError,
    SecretStorageViolationError,
    UnauthorizedDiscoveryError,
)
from app.environment.schemas import (
    EnvironmentType,
    NodeType,
    ScopeType,
)
from app.environment.snapshots import SnapshotManager
from app.environment.storage import StorageContentIngestionError, StorageModelManager


def test_secret_scrubbing_and_rejection():
    """Prompt #6, #52, #187: Never store secret values in the digital twin."""
    # 1. Inspect metadata with raw private key raises SecretStorageViolationError
    bad_meta = {"api_key": "ghp_1234567890abcdefghijklmnopqrstuvwxyz"}
    with pytest.raises(SecretStorageViolationError):
        EnvironmentSafetyGuard.inspect_and_sanitize_metadata(bad_meta, raise_on_secret=True)

    # 2. Secret reference (e.g. key ending with _ref or starts with vault://) is preserved safely
    safe_meta = {"db_password_ref": "vault://secrets/db-pass", "api_key_id": "key_9981"}
    sanitized = EnvironmentSafetyGuard.inspect_and_sanitize_metadata(safe_meta, raise_on_secret=True)
    assert sanitized["db_password_ref"] == "vault://secrets/db-pass"
    assert sanitized["api_key_id"] == "key_9981"


def test_database_and_storage_content_protection():
    """Prompt #24, #42: Do not ingest database or storage file contents."""
    with pytest.raises(DatabaseContentIngestionError):
        DatabaseModelManager.create_database_node(
            database_id="db_01",
            name="users_db",
            engine="PostgreSQL",
            version="15.2",
            environment="PRODUCTION",
            endpoint_ref="ref://db_main",
            raw_content_payload=[{"id": 1, "username": "alice", "email": "alice@example.com"}],
        )

    with pytest.raises(StorageContentIngestionError):
        StorageModelManager.create_storage_node(
            storage_id="bkt_01",
            name="customer-docs",
            storage_type=NodeType.BUCKET,
            capacity_bytes=1000000,
            used_bytes=500000,
            raw_blob_data=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...",
        )


def test_process_and_network_privacy_boundaries():
    """Prompt #18, #38, #182, #183: Respect process, network, and cloud boundaries."""
    # Unauthorized process inspection raises UnauthorizedDiscoveryError
    with pytest.raises(UnauthorizedDiscoveryError):
        ProcessModelManager.create_process_node(
            pid=9999,
            name="user_personal_browser.exe",
            host_id="host_workstation_1",
            authorized_names={"python", "node", "uvicorn"},
        )

    # Unauthorized network inspection raises UnauthorizedDiscoveryError
    with pytest.raises(UnauthorizedDiscoveryError):
        NetworkModelManager.create_network_node(
            network_id="vpc_secret",
            name="private_perimeter_net",
            cidr_block="10.200.0.0/16",
            is_authorized=False,
        )

    # Unauthorized cloud account raises UnauthorizedDiscoveryError
    with pytest.raises(UnauthorizedDiscoveryError):
        CloudModelManager.create_cloud_resource_node(
            resource_id="res_01",
            provider="aws",
            service_category="compute",
            resource_type=NodeType.RESOURCE,
            name="prod-worker",
            region="us-east-1",
            account_or_project_id="acc_unauthorized_999",
            authorized_accounts={"acc_staging_123", "acc_prod_456"},
        )


def test_cross_environment_pollution_prevention():
    """Prompt #29: Do not confuse development with production."""
    with pytest.raises(ProductionSafetyViolationError):
        EnvironmentManager.assert_no_cross_environment_pollution(
            env_a=EnvironmentType.DEVELOPMENT,
            env_b=EnvironmentType.PRODUCTION,
        )


def test_future_leakage_prevention():
    """Prompt #69, #207: Historical state must not use future observations."""
    twin = DigitalTwinEngine.create_twin(scope=ScopeType.SYSTEM)
    t0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 3, 12, 0, tzinfo=timezone.utc)

    twin.timestamp = t1
    snap_t1 = SnapshotManager.create_snapshot(twin)

    twin.timestamp = t2
    snap_t2 = SnapshotManager.create_snapshot(twin)

    # As of Sept 1: neither snapshot existed yet -> returns None
    assert SnapshotManager.reconstruct_as_of([snap_t1, snap_t2], as_of_time=t0) is None

    # As of Sept 2: returns snap_t1, does not leak snap_t2
    recon = SnapshotManager.reconstruct_as_of([snap_t1, snap_t2], as_of_time=t1)
    assert recon is not None
    assert recon.timestamp == t1


def test_reconciliation_conflict_preservation():
    """Prompt #78, #79: Disagreement between non-authoritative sources must preserve conflict, not silently resolve."""
    val, conflict = ReconciliationEngine.reconcile_observations(
        node_type=NodeType.SERVICE,
        resource_id="svc_search",
        observation_a={"source": "telemetry_agent_a", "value": "HEALTHY"},
        observation_b={"source": "telemetry_agent_b", "value": "DEGRADED"},
    )
    assert conflict is not None
    assert conflict.resource == "svc_search"
    assert conflict.value_a == "HEALTHY"
    assert conflict.value_b == "DEGRADED"
    assert conflict.resolved is False


def test_stale_authorization_and_approval():
    """Prompt #131, #132: Stale authorization and approval tokens are rejected."""
    # Stale authorization (>30 mins old) is rejected
    old_auth = datetime.now(timezone.utc) - timedelta(minutes=45)
    with pytest.raises(ProductionSafetyViolationError):
        EnvironmentAuthorizationEngine.validate_action_authorization(
            actor="admin",
            action="restart_service",
            target_environment="PRODUCTION",
            auth_issued_at=old_auth,
        )

    # Stale approval where baseline changed is rejected
    approval_token = {
        "approved_state_baseline": {"version": "1.0", "replicas": 3}
    }
    mutated_state = {"version": "1.0", "replicas": 5}
    with pytest.raises(ProductionSafetyViolationError):
        EnvironmentAuthorizationEngine.validate_approval_freshness(approval_token, mutated_state)
