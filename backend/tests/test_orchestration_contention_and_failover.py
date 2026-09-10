"""Unit and integration tests for resource contention, dynamic failovers, non-idempotency, and recovery (Task 59)."""


from app.orchestration.contention import ContentionResolver
from app.orchestration.recovery import RecoveryEngine
from app.orchestration.resource_registry import ResourceRegistry
from app.orchestration.resources import create_resource
from app.orchestration.schemas import (
    ProviderAssignment,
    RiskSeverity,
    TaskCapabilityRequirement,
)


def test_contention_detection_and_wave_resolution():
    """Verify concurrent tasks competing for a shared constrained resource are sequenced into waves."""
    reg = ResourceRegistry()
    # Resource with capacity 10
    res = create_resource(
        name="DB Connections",
        total_capacity=10.0,
        resource_id="res_db",
    )
    reg.register(res)

    resolver = ContentionResolver(reg)

    # 3 concurrent tasks, each demanding 6 DB connections (total 18 > 10)
    task1 = TaskCapabilityRequirement(
        task_id="task_1",
        priority=3,
        required_resources=[{"resource_id": "res_db", "amount": 6.0}],
    )
    task2 = TaskCapabilityRequirement(
        task_id="task_2",
        priority=2,
        required_resources=[{"resource_id": "res_db", "amount": 6.0}],
    )
    task3 = TaskCapabilityRequirement(
        task_id="task_3",
        priority=1,
        required_resources=[{"resource_id": "res_db", "amount": 6.0}],
    )

    conflicts = resolver.detect_contention([task1, task2, task3])
    assert len(conflicts) == 1
    assert conflicts[0]["total_demanded"] == 18.0
    assert conflicts[0]["available_capacity"] == 10.0

    # Resolving contention partitions them into conflict-free waves
    waves = resolver.resolve_contention([task1, task2, task3])
    assert len(waves) == 3  # Each task gets its own wave since 6+6=12 > 10
    assert waves[0][0].task_id == "task_1"  # Highest priority first


def test_recovery_non_idempotent_operation_blocks_blind_retry():
    """Test Invariant 6 & 83: Non-idempotent/irreversible operations prohibit blind automatic retry."""
    recovery = RecoveryEngine()

    req = TaskCapabilityRequirement(
        task_id="task_payment_01",
        is_irreversible=True,  # Non-idempotent financial/destructive action
    )
    asgn = ProviderAssignment(
        task_id="task_payment_01",
        provider_name="StripeAPI",
        capability_id="cap_pay",
        fallback_provider="PayPalAPI",
    )

    action = recovery.handle_task_failure(
        task_id="task_payment_01",
        assignment=asgn,
        requirement=req,
        error_message="Gateway connection reset",
    )

    assert action["action"] == "HUMAN_INTERVENTION"
    assert "non-idempotent/irreversible" in action["reason"].lower()


def test_recovery_unknown_execution_state_requires_reconciliation():
    """Test Invariant 27 & 87: Unknown execution state requires reconciliation, not optimistic retry."""
    recovery = RecoveryEngine()

    req = TaskCapabilityRequirement(
        task_id="task_cluster_deploy",
        is_irreversible=False,
    )
    asgn = ProviderAssignment(
        task_id="task_cluster_deploy",
        provider_name="K8sDeployer",
        capability_id="cap_deploy",
    )

    action = recovery.handle_task_failure(
        task_id="task_cluster_deploy",
        assignment=asgn,
        requirement=req,
        error_message="Connection timed out while waiting for cluster ACK",
        execution_state="UNKNOWN",
    )

    assert action["action"] == "RECONCILE"
    assert "uncertain" in action["reason"].lower()


def test_recovery_bounded_retries_and_failover():
    """Verify bounded retry progression before dynamic failover to fallback provider."""
    recovery = RecoveryEngine()

    req = TaskCapabilityRequirement(task_id="task_fetch", is_irreversible=False)
    asgn = ProviderAssignment(
        task_id="task_fetch",
        provider_name="FastScraper",
        capability_id="cap_scrape",
        fallback_provider="BackupScraper",
    )

    # Attempt 1 -> Retry
    act1 = recovery.handle_task_failure("task_fetch", asgn, req, "HTTP 503", max_retries=2)
    assert act1["action"] == "RETRY"
    assert act1["attempt"] == 1

    # Attempt 2 -> Retry
    act2 = recovery.handle_task_failure("task_fetch", asgn, req, "HTTP 503", max_retries=2)
    assert act2["action"] == "RETRY"
    assert act2["attempt"] == 2

    # Attempt 3 (retries exhausted) -> Dynamic Failover
    act3 = recovery.handle_task_failure("task_fetch", asgn, req, "HTTP 503", max_retries=2)
    assert act3["action"] == "FAILOVER"
    assert act3["previous_provider"] == "FastScraper"
    assert act3["new_provider"] == "BackupScraper"


def test_recovery_evaluates_fallback_risk():
    """Verify fallback difference detection when fallback carries higher risk."""
    recovery = RecoveryEngine()
    # Primary LOW, Fallback HIGH -> Elevated risk detected
    elevated = recovery.evaluate_fallback_risk(RiskSeverity.LOW, RiskSeverity.HIGH)
    assert elevated is True

    # Primary MEDIUM, Fallback LOW -> Not elevated
    not_elevated = recovery.evaluate_fallback_risk(RiskSeverity.MEDIUM, RiskSeverity.LOW)
    assert not_elevated is False
