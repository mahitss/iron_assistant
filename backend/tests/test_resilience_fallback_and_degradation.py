"""Tests for fallback hierarchies, scope invariance, data classification, and graceful degradation."""

import pytest

from app.resilience.degradation import DegradationManager, ServiceDegradedError
from app.resilience.dedupe import EventDedupeManager
from app.resilience.fallback import FallbackRouter, FallbackSecurityViolationError
from app.resilience.health import DependencyHealthTracker
from app.resilience.schemas import DependencyHealth, SideEffectType


@pytest.mark.asyncio
async def test_fallback_router_target_and_environment_invariance():
    """Verifies that fallbacks can never mutate target or jump environment boundaries."""
    router = FallbackRouter()

    # Attempting to fallback from staging to production is strictly blocked!
    with pytest.raises(FallbackSecurityViolationError) as exc_env:
        router.validate_fallback_target(
            original_target="db_staging",
            fallback_target="db_staging",
            original_environment="staging",
            fallback_environment="production",
        )
    assert "Environment boundary violation" in str(exc_env.value)

    # Attempting to mutate target during fallback is strictly blocked!
    with pytest.raises(FallbackSecurityViolationError) as exc_tgt:
        router.validate_fallback_target(
            original_target="primary_repo",
            fallback_target="shadow_repo",
        )
    assert "Target mutation violation" in str(exc_tgt.value)


@pytest.mark.asyncio
async def test_fallback_router_data_classification_preservation():
    """Verifies that RESTRICTED data cannot be routed to unapproved providers during fallback."""
    router = FallbackRouter()

    # CONFIDENTIAL allows openai / anthropic
    router.validate_data_classification(
        data_classification="CONFIDENTIAL",
        target_provider="anthropic",
    )

    # RESTRICTED prohibits unapproved third-party cloud provider
    with pytest.raises(FallbackSecurityViolationError) as exc_data:
        router.validate_data_classification(
            data_classification="RESTRICTED",
            target_provider="unapproved_cloud",
        )
    assert "prohibits fallback to provider" in str(exc_data.value)


@pytest.mark.asyncio
async def test_fallback_cascade_execution():
    """Verifies multi-tier fallback cascade when primary provider fails."""
    router = FallbackRouter()

    async def primary():
        raise RuntimeError("Primary provider down")

    async def fallback_1():
        raise RuntimeError("Fallback 1 down")

    async def fallback_2():
        return "SUCCESS_FROM_FALLBACK_2"

    result = await router.execute_with_fallback(
        primary_callable=primary,
        primary_provider="primary_llm",
        fallback_callables=[
            ("fallback_llm_1", fallback_1),
            ("fallback_llm_2", fallback_2),
        ],
        operation="complete_prompt",
        data_classification="INTERNAL",
    )
    assert result == "SUCCESS_FROM_FALLBACK_2"
    assert router.fallback_count == 2


@pytest.mark.asyncio
async def test_degradation_read_only_mode_blocks_writes():
    """Verifies that read-only degraded mode blocks state-mutating operations but permits reads."""
    degradation_mgr = DegradationManager()

    # Normal mode allows writes
    degradation_mgr.check_operation_permitted(SideEffectType.NON_IDEMPOTENT_WRITE)
    degradation_mgr.check_operation_permitted(SideEffectType.READ_ONLY)

    # Enable read-only mode (e.g. database secondary replica or DB write failure)
    degradation_mgr.set_read_only_mode(True)

    # Read operations still permitted
    degradation_mgr.check_operation_permitted(SideEffectType.READ_ONLY)

    # Write operations are blocked!
    with pytest.raises(ServiceDegradedError):
        degradation_mgr.check_operation_permitted(SideEffectType.IDEMPOTENT_WRITE)

    with pytest.raises(ServiceDegradedError):
        degradation_mgr.check_operation_permitted(SideEffectType.NON_IDEMPOTENT_WRITE)


@pytest.mark.asyncio
async def test_optional_feature_shedding():
    """Verifies that optional features (e.g. analytics or recommendations) shed without failing core tasks."""
    degradation_mgr = DegradationManager()

    async def flaky_analytics():
        raise ConnectionError("Analytics pipeline unreachable")

    # Optional feature returns fallback value safely
    val = await degradation_mgr.execute_optional_feature(
        feature_name="analytics_dispatch",
        feature_callable=flaky_analytics,
        default_fallback_value={"status": "shed"},
    )
    assert val == {"status": "shed"}


def test_dependency_health_and_readiness():
    """Verifies that dependency health reports distinguish liveness from readiness."""
    tracker = DependencyHealthTracker()

    # When all is healthy
    tracker.record_dependency_status("database", DependencyHealth.HEALTHY)
    is_live, _ = tracker.evaluate_liveness()
    is_ready, _ = tracker.evaluate_readiness()
    assert is_live is True
    assert is_ready is True

    # When critical DB is unavailable -> still alive, but NOT READY!
    tracker.record_dependency_status("database", DependencyHealth.UNAVAILABLE)
    is_live, _ = tracker.evaluate_liveness()
    is_ready, ready_msg = tracker.evaluate_readiness()
    assert is_live is True
    assert is_ready is False
    assert "Database is unavailable" in ready_msg


def test_event_deduplication_and_version_ordering():
    """Verifies sliding-window deduplication and rejection of stale events."""
    dedupe = EventDedupeManager(ttl_seconds=3600)

    # Event 1 is new
    assert dedupe.is_duplicate_event("evt_101") is False

    # Immediate duplicate of Event 1 is suppressed
    assert dedupe.is_duplicate_event("evt_101") is True

    # Monotonic version ordering for entity "task_99"
    assert dedupe.is_stale_event("task_99", event_version=1) is False
    assert dedupe.is_stale_event("task_99", event_version=2) is False

    # Old event arriving out of order (v1 after v2) is rejected as stale!
    assert dedupe.is_stale_event("task_99", event_version=1) is True
    assert dedupe.is_stale_event("task_99", event_version=2) is True  # Same version also rejected
