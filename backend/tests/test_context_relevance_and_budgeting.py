"""Unit tests for Relevance Scoring, 7-Level Budgeting, and Compression (Task 69)."""

from datetime import UTC, datetime

from app.context.budgeting import ContextBudgeter
from app.context.compression import ContextCompressor
from app.context.relevance import ContextRelevanceEngine
from app.context.universal_schemas import (
    ContextHierarchyLevel,
    ContextPriorityTier,
    ContextRequest,
    UniversalContextItem,
    UniversalContextType,
)


def test_multi_factor_relevance_scoring_and_penalties():
    """Verify relevance engine boosts aligned items and penalizes stale/mismatched items."""
    req = ContextRequest(
        query="Database connection timeout in production cluster",
        intent="database_timeout",
        environment="production",
    )

    now = datetime.now(UTC)

    # 1. Matching item in production with high confidence
    item_aligned = UniversalContextItem(
        item_id="it_aligned",
        context_type=UniversalContextType.MEMORY_CONTEXT,
        source_id="mem_1",
        source_type="memory",
        title="Database configuration",
        content="Production database connection timeout is configured to 30 seconds",
        hierarchy_level=ContextHierarchyLevel.LEVEL_5_LONG_TERM_MEMORY,
        priority_tier=ContextPriorityTier.HIGH,
        relevance_score=0.8,
        freshness_score=1.0,
        confidence=1.0,
        environment="production",
        timestamp=now,
    )

    # 2. Mismatched environment item (staging)
    item_mismatch = UniversalContextItem(
        item_id="it_staging",
        context_type=UniversalContextType.MEMORY_CONTEXT,
        source_id="mem_2",
        source_type="memory",
        title="Database configuration staging",
        content="Staging database connection timeout is 10 seconds",
        hierarchy_level=ContextHierarchyLevel.LEVEL_5_LONG_TERM_MEMORY,
        priority_tier=ContextPriorityTier.NORMAL,
        relevance_score=0.8,
        freshness_score=1.0,
        confidence=1.0,
        environment="staging",
        timestamp=now,
    )

    # 3. Stale item
    item_stale = UniversalContextItem(
        item_id="it_stale",
        context_type=UniversalContextType.MEMORY_CONTEXT,
        source_id="mem_3",
        source_type="memory",
        title="Old Database configuration",
        content="Database connection timeout previously failed",
        hierarchy_level=ContextHierarchyLevel.LEVEL_5_LONG_TERM_MEMORY,
        priority_tier=ContextPriorityTier.NORMAL,
        relevance_score=0.8,
        freshness_score=0.2,  # Stale
        confidence=1.0,
        environment="production",
        timestamp=now,
    )

    score_aligned, reason_aligned = ContextRelevanceEngine.score_candidate(item_aligned, req)
    score_mismatch, reason_mismatch = ContextRelevanceEngine.score_candidate(item_mismatch, req)
    score_stale, reason_stale = ContextRelevanceEngine.score_candidate(item_stale, req)

    # Aligned item must outrank both environment mismatch and stale items
    assert score_aligned > score_mismatch
    assert score_aligned > score_stale
    assert "Direct environment match 'production'" in reason_aligned
    assert "Environment mismatch" in reason_mismatch
    assert "Staleness penalty applied" in reason_stale


def test_seven_level_hierarchy_and_token_budgeting():
    """Verify budget allocation prioritizes Level 0/1 tasks and critical tiers within token limits."""
    # Create items across levels
    items = [
        UniversalContextItem(
            item_id=f"it_kb_{i}",
            context_type=UniversalContextType.KNOWLEDGE_CONTEXT,
            source_id=f"kb_{i}",
            source_type="kb",
            title=f"General Knowledge {i}",
            content=f"Detailed architectural documentation notes and broad reference guide paragraph {i} "
            * 10,
            hierarchy_level=ContextHierarchyLevel.LEVEL_6_GENERAL_KNOWLEDGE,
            priority_tier=ContextPriorityTier.LOW,
            relevance_score=0.7,
        )
        for i in range(10)
    ]

    task_item = UniversalContextItem(
        item_id="it_task",
        context_type=UniversalContextType.TASK_CONTEXT,
        source_id="task_1",
        source_type="task",
        title="Current Deploy Task",
        content="Deploying v2.4 to production cluster",
        hierarchy_level=ContextHierarchyLevel.LEVEL_0_TASK,
        priority_tier=ContextPriorityTier.CRITICAL,
        relevance_score=0.9,
    )
    items.append(task_item)

    # Allocate with tight token budget
    selected, excluded, tokens, needs_comp = ContextBudgeter.allocate_budget(
        ranked_items=items,
        max_tokens=250,
        max_items=5,
    )

    # Task item must be selected despite tight budget
    selected_ids = {it.item_id for it in selected}
    assert "it_task" in selected_ids
    assert tokens <= 250
    assert len(selected) <= 5
    assert len(excluded) > 0


def test_context_compression_with_provenance_dag():
    """Verify context compressor summarizes overflowing items while preserving source provenance."""
    excluded = [
        UniversalContextItem(
            item_id=f"it_err_{i}",
            context_type=UniversalContextType.INCIDENT_CONTEXT,
            source_id=f"err_log_{i}",
            source_type="system_logs",
            title=f"Timeout Log {i}",
            content=f"Worker {i} experienced TCP connection timeout to auth service at port 5432",
            hierarchy_level=ContextHierarchyLevel.LEVEL_4_RECENT_HISTORY,
            priority_tier=ContextPriorityTier.NORMAL,
            relevance_score=0.75,
            freshness_score=1.0,
        )
        for i in range(4)
    ]

    compressed = ContextCompressor.compress_overflow(
        selected_items=[],
        excluded_items=excluded,
        target_token_budget=1000,
    )

    assert len(compressed) == 1
    summary = compressed[0]
    assert summary.is_compressed is True
    assert summary.context_type == UniversalContextType.INCIDENT_CONTEXT
    assert "Consolidated summary of 4 INCIDENT_CONTEXT items" in summary.content
    # Provenance preserved
    assert len(summary.derived_from_ids) == 4
    assert "it_err_0" in summary.derived_from_ids
    assert "it_err_3" in summary.derived_from_ids
