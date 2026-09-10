"""Unit and integration tests for resource modeling, reservations, capacity math, and leak detection (Task 59)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.orchestration.resource_registry import ResourceRegistry
from app.orchestration.resources import create_resource
from app.orchestration.safety import (
    OrchestrationSafetyError,
    ResourceContentionError,
)
from app.orchestration.schemas import (
    HealthStatus,
    ResourceStatus,
    ResourceType,
)


def test_resource_creation_and_capacity():
    """Verify resource creation and initial available capacity accounting."""
    res = create_resource(
        name="Worker Pool A",
        resource_type=ResourceType.COMPUTE,
        total_capacity=100.0,
        unit="vCPU",
        environment="production",
    )
    assert res.total_capacity == 100.0
    assert res.available_capacity == 100.0
    assert res.allocated_capacity == 0.0
    assert res.reserved_capacity == 0.0
    assert res.status == ResourceStatus.AVAILABLE


def test_resource_reservation_and_release():
    """Verify reservation decreases available capacity and increases reserved capacity."""
    reg = ResourceRegistry()
    res = create_resource(
        name="Cluster B",
        total_capacity=50.0,
        resource_id="res_cluster_b",
    )
    reg.register(res)

    future_exp = datetime.now(timezone.utc) + timedelta(hours=2)
    rsv = reg.reserve(
        resource_id="res_cluster_b",
        owner="MigrationTeam",
        purpose="Database migration compute reserve",
        amount=20.0,
        expires_at=future_exp,
    )

    assert rsv.is_active is True
    assert res.reserved_capacity == 20.0
    assert res.available_capacity == 30.0
    assert res.status == ResourceStatus.RESERVED

    # Releasing reservation restores available capacity
    released = reg.release_reservation(rsv.reservation_id)
    assert released is True
    assert res.reserved_capacity == 0.0
    assert res.available_capacity == 50.0
    assert res.status == ResourceStatus.AVAILABLE


def test_overcapacity_reservation_blocked():
    """Test Invariant: Cannot reserve or allocate beyond available capacity."""
    reg = ResourceRegistry()
    res = create_resource(
        name="DB Pool",
        total_capacity=10.0,
        resource_id="res_db_pool",
    )
    reg.register(res)

    future_exp = datetime.now(timezone.utc) + timedelta(minutes=30)
    with pytest.raises(ResourceContentionError, match="Insufficient capacity"):
        reg.reserve(
            resource_id="res_db_pool",
            owner="Dev1",
            purpose="Testing",
            amount=15.0,  # Requesting 15 out of 10
            expires_at=future_exp,
        )


def test_unhealthy_or_unknown_resource_cannot_be_reserved():
    """Test Invariant 8 & 9: Degraded/unhealthy/unknown resource health blocks reservation."""
    reg = ResourceRegistry()
    res = create_resource(
        name="Flaky API",
        health=HealthStatus.UNAVAILABLE,
        resource_id="res_flaky_api",
    )
    reg.register(res)

    future_exp = datetime.now(timezone.utc) + timedelta(minutes=10)
    with pytest.raises(ResourceContentionError, match="resource health is UNAVAILABLE"):
        reg.reserve(
            resource_id="res_flaky_api",
            owner="Dev1",
            purpose="Testing",
            amount=1.0,
            expires_at=future_exp,
        )


def test_expired_reservation_cleanup_and_leak_detection():
    """Verify expired reservations are auto-unlocked and do not cause resource leaks."""
    reg = ResourceRegistry()
    res = create_resource(
        name="Memory Cache",
        total_capacity=20.0,
        resource_id="res_mem_cache",
    )
    reg.register(res)

    # Create a reservation that has already expired
    past_exp = datetime.now(timezone.utc) - timedelta(minutes=5)
    reg.reserve(
        resource_id="res_mem_cache",
        owner="OrphanJob",
        purpose="Stale batch job",
        amount=10.0,
        expires_at=past_exp,
    )

    assert res.available_capacity == 10.0

    # Running clean_expired_reservations auto-releases it
    cleaned = reg.clean_expired_reservations()
    assert cleaned == 1
    assert res.available_capacity == 20.0
    assert res.reserved_capacity == 0.0

    # Leak detection should now report 0 leaks
    leaks = reg.detect_leaks()
    assert len(leaks) == 0


def test_resource_isolation_and_ownership():
    """Test Invariant 51 & 140: Multi-tenant ownership prevents cross-tenant reservation consumption."""
    reg = ResourceRegistry()
    res = create_resource(
        name="Isolated Storage",
        total_capacity=100.0,
        resource_id="res_storage",
    )
    reg.register(res)

    future_exp = datetime.now(timezone.utc) + timedelta(hours=1)
    rsv = reg.reserve(
        resource_id="res_storage",
        owner="ProjectAlpha",
        purpose="Alpha dedicated storage",
        amount=40.0,
        expires_at=future_exp,
    )

    # ProjectBeta attempts to consume ProjectAlpha's reservation
    with pytest.raises(OrchestrationSafetyError, match="Resource isolation violation"):
        reg.allocate(
            resource_id="res_storage",
            amount=20.0,
            reservation_id=rsv.reservation_id,
            owner="ProjectBeta",
        )

    # ProjectAlpha can consume its own reservation
    success = reg.allocate(
        resource_id="res_storage",
        amount=20.0,
        reservation_id=rsv.reservation_id,
        owner="ProjectAlpha",
    )
    assert success is True
    assert res.allocated_capacity == 20.0
    assert res.reserved_capacity == 20.0
