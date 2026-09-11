"""Unit tests for Context Request and Multi-Source Discovery (Task 69)."""

import pytest

from app.context.discovery import ContextDiscoveryEngine
from app.context.universal_schemas import (
    ContextHierarchyLevel,
    ContextPriorityTier,
    ContextRequest,
    UniversalContextItem,
    UniversalContextType,
)


@pytest.mark.asyncio
async def test_context_request_model_and_defaults():
    """Verify ContextRequest initializes with valid boundaries and defaults."""
    req = ContextRequest(
        tenant_id="tenant_alpha",
        user_id="alice",
        query="Investigate API performance degradation",
        intent="performance_audit",
        environment="production",
        maximum_tokens=2500,
        maximum_items=15,
    )
    assert req.tenant_id == "tenant_alpha"
    assert req.user_id == "alice"
    assert req.environment == "production"
    assert req.maximum_tokens == 2500
    assert req.maximum_items == 15
    assert req.freshness_requirement == "STANDARD"
    assert req.context_request_id.startswith("req_")


@pytest.mark.asyncio
async def test_multi_source_discovery_engine():
    """Verify discovery engine gathers immediate task, session, environment, and injected sources."""
    discovery = ContextDiscoveryEngine()
    req = ContextRequest(
        tenant_id="tenant_alpha",
        user_id="alice",
        session_id="sess_001",
        task_id="task_audit_99",
        task_type="INCIDENT_INVESTIGATION",
        query="Investigate why service crashed",
        environment="production",
    )

    custom_item = UniversalContextItem(
        item_id="item_incident_01",
        context_type=UniversalContextType.INCIDENT_CONTEXT,
        source_id="inc_42",
        source_type="incident_response",
        title="Active Incident: High 500 error rate",
        content="Service backend reported 15% HTTP 500 errors",
        hierarchy_level=ContextHierarchyLevel.LEVEL_4_RECENT_HISTORY,
        priority_tier=ContextPriorityTier.HIGH,
        relevance_score=0.92,
        freshness_score=1.0,
        confidence=1.0,
        trust_level="VERIFIED",
        importance=0.9,
        environment="production",
    )

    candidates = await discovery.discover_candidates(req, additional_items=[custom_item])

    assert len(candidates) >= 4
    types = {c.context_type for c in candidates}
    assert UniversalContextType.TASK_CONTEXT in types
    assert UniversalContextType.SESSION_CONTEXT in types
    assert UniversalContextType.ENVIRONMENT_CONTEXT in types
    assert UniversalContextType.INCIDENT_CONTEXT in types

    task_item = next(c for c in candidates if c.context_type == UniversalContextType.TASK_CONTEXT)
    assert task_item.priority_tier == ContextPriorityTier.CRITICAL
    assert task_item.hierarchy_level == ContextHierarchyLevel.LEVEL_0_TASK


@pytest.mark.asyncio
async def test_discovery_filtering_excluded_types_and_freshness():
    """Verify discovery engine filters out excluded context types and stale items when FRESH_ONLY requested."""
    discovery = ContextDiscoveryEngine()
    req = ContextRequest(
        query="Check system status",
        excluded_context_types=[UniversalContextType.SESSION_CONTEXT],
        freshness_requirement="FRESH_ONLY",
        minimum_confidence=0.7,
    )

    stale_item = UniversalContextItem(
        item_id="item_stale",
        context_type=UniversalContextType.MEMORY_CONTEXT,
        source_id="mem_old",
        source_type="memory",
        title="Old status report",
        content="System was running smoothly 2 months ago",
        relevance_score=0.8,
        freshness_score=0.3,  # Stale (< 0.8)
        confidence=0.9,
    )

    low_conf_item = UniversalContextItem(
        item_id="item_untrusted",
        context_type=UniversalContextType.KNOWLEDGE_CONTEXT,
        source_id="kb_rumor",
        source_type="unverified_notes",
        title="Unverified claim",
        content="Maybe server ran out of memory",
        relevance_score=0.8,
        freshness_score=1.0,
        confidence=0.4,  # Low confidence (< 0.7)
    )

    candidates = await discovery.discover_candidates(req, additional_items=[stale_item, low_conf_item])
    candidate_ids = {c.item_id for c in candidates}

    # Stale item filtered out by FRESH_ONLY
    assert "item_stale" not in candidate_ids
    # Low confidence item filtered out
    assert "item_untrusted" not in candidate_ids
    # Session context excluded
    assert not any(c.context_type == UniversalContextType.SESSION_CONTEXT for c in candidates)
