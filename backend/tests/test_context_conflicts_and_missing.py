"""Unit tests for Context Conflict, Missing Context, and Quality Scoring (Task 69)."""

from datetime import UTC, datetime, timedelta

from app.context.conflicts import ContextConflictDetector
from app.context.missing import MissingContextDetector
from app.context.quality import ContextQualityEvaluator
from app.context.universal_schemas import (
    ContextRequest,
    UniversalContextItem,
    UniversalContextType,
)


def test_polarity_conflict_detection():
    """Verify opposite polarity assertions on the same subject are detected as conflicts."""
    now = datetime.now(UTC)
    item_a = UniversalContextItem(
        item_id="it_healthy",
        context_type=UniversalContextType.ENVIRONMENT_CONTEXT,
        source_id="twin_1",
        source_type="environment_twin",
        title="Payment Service Health",
        content="Payment Service is fully healthy and responding to all health probes",
        timestamp=now - timedelta(hours=2),
    )
    item_b = UniversalContextItem(
        item_id="it_unhealthy",
        context_type=UniversalContextType.INCIDENT_CONTEXT,
        source_id="incident_99",
        source_type="monitoring",
        title="Payment Service Health Alert",
        content="Payment Service is currently unhealthy with failing readiness checks",
        timestamp=now,
    )

    conflicts = ContextConflictDetector.detect_conflicts([item_a, item_b])
    assert len(conflicts) == 1
    c = conflicts[0]
    assert "healthy" in c.reason and "unhealthy" in c.reason
    assert c.resolution_status == "TEMPORAL_SUPERSEDED"
    assert "newer" in c.temporal_difference


def test_property_mismatch_conflict_detection():
    """Verify divergent property assignments are flagged as conflicts."""
    item_a = UniversalContextItem(
        item_id="it_cfg_1",
        context_type=UniversalContextType.MEMORY_CONTEXT,
        source_id="mem_1",
        source_type="memory",
        title="Redis Configuration A",
        content="Redis cluster timeout: 30s with max connections 100",
    )
    item_b = UniversalContextItem(
        item_id="it_cfg_2",
        context_type=UniversalContextType.MEMORY_CONTEXT,
        source_id="mem_2",
        source_type="memory",
        title="Redis Configuration B",
        content="Redis cluster timeout: 60s with max connections 100",
    )

    conflicts = ContextConflictDetector.detect_conflicts([item_a, item_b])
    assert len(conflicts) == 1
    assert "timeout" in conflicts[0].reason
    assert "30s" in conflicts[0].reason
    assert "60s" in conflicts[0].reason


def test_missing_context_detection():
    """Verify missing context detector catches absent error logs for debug queries and absent config for deploy queries."""
    # 1. Debug query with no stacktraces
    req_debug = ContextRequest(
        query="Help me debug this unexpected server crash and failure",
        intent="debug_crash",
    )
    items_debug = [
        UniversalContextItem(
            item_id="it_general",
            context_type=UniversalContextType.TASK_CONTEXT,
            source_id="task_1",
            source_type="task",
            title="General task",
            content="Looking at system crash",
        )
    ]
    missing_debug = MissingContextDetector.detect_missing_context(req_debug, items_debug)
    assert any("Execution Logs" in m.category for m in missing_debug)

    # 2. Deploy query with no environment config
    req_deploy = ContextRequest(
        query="Deploy release v2 to production cluster",
        intent="deploy_service",
    )
    items_deploy = [
        UniversalContextItem(
            item_id="it_task",
            context_type=UniversalContextType.TASK_CONTEXT,
            source_id="task_2",
            source_type="task",
            title="Deployment instruction",
            content="Run deploy command",
        )
    ]
    missing_deploy = MissingContextDetector.detect_missing_context(req_deploy, items_deploy)
    assert any("Environment Configuration" in m.category for m in missing_deploy)


def test_quality_score_evaluation():
    """Verify multi-factor quality scoring computes expected composite score."""
    items = [
        UniversalContextItem(
            item_id="it_1",
            context_type=UniversalContextType.TASK_CONTEXT,
            source_id="t1",
            source_type="task",
            title="Task item",
            content="Perform deployment verification",
            relevance_score=0.95,
            freshness_score=1.0,
            confidence=1.0,
            trust_level="VERIFIED",
        ),
        UniversalContextItem(
            item_id="it_2",
            context_type=UniversalContextType.ENVIRONMENT_CONTEXT,
            source_id="e1",
            source_type="env",
            title="Environment info",
            content="Production Kubernetes cluster state",
            relevance_score=0.88,
            freshness_score=1.0,
            confidence=1.0,
            trust_level="VERIFIED",
        ),
    ]

    quality = ContextQualityEvaluator.evaluate_quality(items, total_candidates=2, build_latency_ms=15.0)
    assert quality.overall_score >= 0.85
    assert quality.relevance >= 0.90
    assert quality.freshness == 1.0
    assert quality.trust == 1.0
    assert quality.latency_ms == 15.0
