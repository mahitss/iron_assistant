"""Tests for deterministic health scores and dynamic service map generation (Task 38)."""

from app.observability.dependencies import DependencyGraphTracker
from app.observability.health import HealthEvaluator
from app.observability.schemas import DependencyHealthState


def test_deterministic_health_score_calculation():
    """Health score is computed deterministically from availability, dependencies, and latency."""
    # 1. Optimal condition
    summary_optimal = HealthEvaluator.calculate_health_score(
        db_healthy=True,
        redis_healthy=True,
        error_rate=0.0,
        latency_p95_ms=15.0,
    )
    assert summary_optimal.score == 100.0
    assert summary_optimal.overall_status == DependencyHealthState.HEALTHY
    assert summary_optimal.availability_percent == 100.0

    # 2. Database outage (critical dependency loss)
    summary_db_down = HealthEvaluator.calculate_health_score(
        db_healthy=False,
        redis_healthy=True,
        error_rate=0.05,
        latency_p95_ms=25.0,
    )
    assert summary_db_down.score <= 60.0
    assert summary_db_down.overall_status == DependencyHealthState.UNAVAILABLE
    assert summary_db_down.dependency_statuses["database"] == DependencyHealthState.UNAVAILABLE.value

    # 3. High latency and elevated errors
    summary_degraded = HealthEvaluator.calculate_health_score(
        db_healthy=True,
        redis_healthy=True,
        error_rate=0.10,
        latency_p95_ms=2500.0,
    )
    assert summary_degraded.score < 85.0
    assert summary_degraded.overall_status == DependencyHealthState.DEGRADED


def test_dynamic_service_map_generation_from_telemetry():
    """DependencyGraphTracker builds live nodes and edges from observed span calls."""
    tracker = DependencyGraphTracker()
    tracker.clear()

    # Record normal calls from API to task_engine
    for _ in range(10):
        tracker.record_call(source="api", target="task_engine", duration_ms=45.0, is_error=False)

    # Record calls from task_engine to external provider with some errors
    for _ in range(8):
        tracker.record_call(source="task_engine", target="provider", duration_ms=650.0, is_error=False)
    for _ in range(2):
        tracker.record_call(source="task_engine", target="provider", duration_ms=1200.0, is_error=True)

    service_map = tracker.generate_service_map()
    assert len(service_map.edges) >= 2

    # Check edges
    edge_map = {(e.source, e.target): e for e in service_map.edges}
    assert ( "api", "task_engine" ) in edge_map
    assert edge_map[("api", "task_engine")].call_count == 10
    assert edge_map[("api", "task_engine")].error_count == 0

    assert ( "task_engine", "provider" ) in edge_map
    assert edge_map[("task_engine", "provider")].call_count == 10
    assert edge_map[("task_engine", "provider")].error_count == 2

    # Check provider node error rate and health
    nodes_map = {n.name: n for n in service_map.nodes}
    assert "provider" in nodes_map
    assert nodes_map["provider"].error_rate == 0.2
    assert nodes_map["provider"].health == DependencyHealthState.DEGRADED
