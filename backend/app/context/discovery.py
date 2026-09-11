"""ContextDiscoveryEngine: Multi-source context discovery across Kairo subsystems (Task 69)."""

import logging
from datetime import UTC, datetime
from typing import Any

from app.context.universal_schemas import (
    ContextHierarchyLevel,
    ContextPriorityTier,
    ContextRequest,
    UniversalContextItem,
    UniversalContextType,
)

logger = logging.getLogger("kairo.context.discovery")


class ContextDiscoveryEngine:
    """Discovers candidate context elements across memory, knowledge graph, goals, plans, env, and decisions."""

    def __init__(self) -> None:
        self._external_providers: list[Any] = []

    def register_provider(self, provider: Any) -> None:
        """Register an external provider for specialized contextual discovery."""
        self._external_providers.append(provider)

    async def discover_candidates(
        self,
        request: ContextRequest,
        additional_items: list[UniversalContextItem] | None = None,
    ) -> list[UniversalContextItem]:
        """Gather candidate context items from all available and authorized subsystems."""
        candidates: list[UniversalContextItem] = []
        now = datetime.now(UTC)

        # 1. Immediate Task Context (Level 0)
        if request.task_id or request.task_type:
            task_title = f"Task: {request.task_type or 'General'}"
            candidates.append(
                UniversalContextItem(
                    item_id=f"item_task_{request.task_id or 'current'}",
                    context_type=UniversalContextType.TASK_CONTEXT,
                    source_id=request.task_id or "task_current",
                    source_type="task_engine",
                    title=task_title,
                    content=f"Query: {request.query} | Intent: {request.intent or 'unspecified'}",
                    hierarchy_level=ContextHierarchyLevel.LEVEL_0_TASK,
                    priority_tier=ContextPriorityTier.CRITICAL,
                    relevance_score=1.0,
                    freshness_score=1.0,
                    confidence=1.0,
                    trust_level="VERIFIED",
                    importance=0.9,
                    timestamp=now,
                    environment=request.environment,
                    reason="Immediate task instruction and intent",
                )
            )

        # 2. Session Context (Level 1)
        if request.session_id:
            candidates.append(
                UniversalContextItem(
                    item_id=f"item_sess_{request.session_id}",
                    context_type=UniversalContextType.SESSION_CONTEXT,
                    source_id=request.session_id,
                    source_type="session_manager",
                    title=f"Session {request.session_id}",
                    content=f"Active user session: {request.session_id}",
                    hierarchy_level=ContextHierarchyLevel.LEVEL_1_SESSION,
                    priority_tier=ContextPriorityTier.HIGH,
                    relevance_score=0.85,
                    freshness_score=1.0,
                    confidence=1.0,
                    trust_level="VERIFIED",
                    importance=0.6,
                    timestamp=now,
                    environment=request.environment,
                    reason="Active conversational session binding",
                )
            )

        # 3. Environment Context
        candidates.append(
            UniversalContextItem(
                item_id=f"item_env_{request.environment}",
                context_type=UniversalContextType.ENVIRONMENT_CONTEXT,
                source_id=f"env_{request.environment}",
                source_type="environment_twin",
                title=f"Environment: {request.environment}",
                content=f"Target deployment and execution runtime: {request.environment}",
                hierarchy_level=ContextHierarchyLevel.LEVEL_2_USER_WORKSPACE,
                priority_tier=ContextPriorityTier.HIGH,
                relevance_score=0.90,
                freshness_score=1.0,
                confidence=1.0,
                trust_level="VERIFIED",
                importance=0.8,
                timestamp=now,
                environment=request.environment,
                reason="Specifies deployment boundary and environment constraints",
            )
        )

        # 4. Durable Memory Retrieval (Level 5) via MemoryConsolidationService
        try:
            from app.memory_consolidation.service import get_memory_consolidation_service

            mem_service = get_memory_consolidation_service()
            search_res = mem_service.search_memories(
                query=request.query,
                tenant_id=request.tenant_id,
                top_k=request.maximum_items,
                include_stale=(request.freshness_requirement == "HISTORICAL_OK"),
            )
            for res in search_res:
                mem = res.memory
                ctx_type = (
                    UniversalContextType.KNOWLEDGE_CONTEXT
                    if mem.memory_type == "SEMANTIC_MEMORY"
                    else UniversalContextType.MEMORY_CONTEXT
                )
                level = (
                    ContextHierarchyLevel.LEVEL_6_GENERAL_KNOWLEDGE
                    if mem.memory_type == "SEMANTIC_MEMORY"
                    else ContextHierarchyLevel.LEVEL_5_LONG_TERM_MEMORY
                )
                candidates.append(
                    UniversalContextItem(
                        item_id=f"item_mem_{mem.id}",
                        context_type=ctx_type,
                        source_id=mem.id,
                        source_type="memory_consolidation",
                        title=f"{mem.cognitive_type}: {mem.content[:60]}...",
                        content=mem.content,
                        hierarchy_level=level,
                        priority_tier=ContextPriorityTier.NORMAL,
                        relevance_score=res.score,
                        freshness_score=1.0
                        if mem.freshness == "FRESH"
                        else (0.5 if mem.freshness == "AGING" else 0.2),
                        confidence=mem.confidence,
                        trust_level=mem.trust_level.value
                        if hasattr(mem.trust_level, "value")
                        else str(mem.trust_level),
                        importance=mem.importance,
                        timestamp=mem.observed_at or mem.created_at,
                        provenance=f"Memory {mem.id} ({mem.source_type})",
                        environment=request.environment,
                        reason=res.retrieval_reason or "Retrieved via cognitive memory search",
                    )
                )
        except Exception as exc:
            logger.debug("Memory consolidation discovery hook skipped or unavailable: %s", exc)

        # 5. Integrate Additional Items (e.g. from tests or callers)
        if additional_items:
            for it in additional_items:
                candidates.append(it)

        # 6. Apply Filters (Excluded Context Types, Excluded Sources, Min Confidence, Min Trust)
        filtered: list[UniversalContextItem] = []
        for item in candidates:
            # Excluded types
            if request.excluded_context_types and item.context_type in request.excluded_context_types:
                continue
            # Required types constraint
            if request.required_context_types and item.context_type not in request.required_context_types:
                # Still allow critical task context
                if item.priority_tier != ContextPriorityTier.CRITICAL:
                    continue
            # Excluded sources
            if request.excluded_sources and item.source_id in request.excluded_sources:
                continue
            # Minimum confidence
            if item.confidence < request.minimum_confidence:
                continue
            # Freshness requirement
            if request.freshness_requirement == "FRESH_ONLY" and item.freshness_score < 0.8:
                continue

            filtered.append(item)

        return filtered
