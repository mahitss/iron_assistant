"""UniversalContextOrchestrator: Central coordinator for the 20-step context lifecycle (Task 69)."""

import logging
import time
from datetime import UTC, datetime

from app.context.budgeting import ContextBudgeter
from app.context.cache import UniversalContextCache
from app.context.compression import ContextCompressor
from app.context.conflicts import ContextConflictDetector
from app.context.discovery import ContextDiscoveryEngine
from app.context.missing import MissingContextDetector
from app.context.personalization import AdaptivePersonalizationEngine
from app.context.quality import ContextQualityEvaluator
from app.context.relevance import ContextRelevanceEngine
from app.context.safety import ContextSafetyGuard
from app.context.schemas import ContextItem, ContextType
from app.context.snapshots import ContextSnapshotManager
from app.context.universal_schemas import (
    ContextHierarchyLevel,
    ContextPackage,
    ContextPriorityTier,
    ContextRequest,
    UniversalContextItem,
    UniversalContextType,
)

logger = logging.getLogger("kairo.context.orchestrator")


class UniversalContextOrchestrator:
    """End-to-end orchestrator for context discovery, relevance scoring, budgeting, conflicts, and assembly."""

    def __init__(
        self,
        discovery_engine: ContextDiscoveryEngine | None = None,
        personalization_engine: AdaptivePersonalizationEngine | None = None,
        cache: UniversalContextCache | None = None,
        snapshot_manager: ContextSnapshotManager | None = None,
    ) -> None:
        self.discovery = discovery_engine or ContextDiscoveryEngine()
        self.personalization = personalization_engine or AdaptivePersonalizationEngine()
        self.cache = cache or UniversalContextCache()
        self.snapshots = snapshot_manager or ContextSnapshotManager()

    async def build_context(
        self,
        request: ContextRequest,
        use_cache: bool = True,
        additional_candidates: list[UniversalContextItem] | None = None,
    ) -> ContextPackage:
        """Execute the complete 20-step context lifecycle to assemble an optimized ContextPackage."""
        start_time = time.perf_counter()

        # 1. Cache Check
        if use_cache:
            cached = self.cache.get(
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                session_id=request.session_id,
                task_id=request.task_id,
                agent_id=request.agent_id,
                environment=request.environment,
                query=request.query,
            )
            if cached:
                logger.debug("Cache hit for context request '%s'", request.context_request_id)
                return cached

        # 2. Context Discovery
        candidates = await self.discovery.discover_candidates(request, additional_items=additional_candidates)

        # 3. Add Personalization Items (Level 2 User Context)
        user_prefs = self.personalization.get_preferences(request.tenant_id, request.user_id)
        for pref in user_prefs:
            pref_content = f"User preference for {pref.category.value} ({pref.key}): {pref.value}"
            candidates.append(
                UniversalContextItem(
                    item_id=f"item_pref_{pref.preference_id}",
                    context_type=UniversalContextType.USER_CONTEXT,
                    source_id=pref.preference_id,
                    source_type="adaptive_personalization",
                    title=f"Preference: {pref.key}",
                    content=pref_content,
                    hierarchy_level=ContextHierarchyLevel.LEVEL_2_USER_WORKSPACE,
                    priority_tier=ContextPriorityTier.HIGH
                    if pref.confidence.value in {"HIGH", "EXPLICIT"}
                    else ContextPriorityTier.NORMAL,
                    relevance_score=0.75 if pref.confidence.value in {"HIGH", "EXPLICIT"} else 0.50,
                    freshness_score=1.0,
                    confidence=pref.confidence_score,
                    trust_level="USER_PREFERENCE",
                    importance=0.6,
                    timestamp=pref.updated_at,
                    reason=f"Active user operational preference ({pref.source.value}, confidence: {pref.confidence.value})",
                )
            )

        # 4. Sanitize items against credentials and prompt injection
        sanitized_candidates: list[UniversalContextItem] = []
        for it in candidates:
            # Adapt to ContextSafetyGuard
            legacy_item = ContextItem(
                source_type=ContextType.MEMORY_CONTEXT,
                source_id=it.source_id,
                title=it.title,
                content=it.content,
                relevance_score=it.relevance_score,
                confidence=it.confidence,
                timestamp=it.timestamp,
                reason=it.reason,
            )
            clean_legacy = ContextSafetyGuard.sanitize_item(legacy_item)
            clean_content = clean_legacy.content if clean_legacy else it.content
            sanitized_candidates.append(it.model_copy(update={"content": clean_content}))

        # 5. Multi-factor Relevance Scoring & Ranking
        ranked_items = ContextRelevanceEngine.rank_items(sanitized_candidates, request)

        # 6. Budget Allocation across 7-level hierarchy
        selected, excluded, token_est, needs_compression = ContextBudgeter.allocate_budget(
            ranked_items=ranked_items,
            max_tokens=request.maximum_tokens,
            max_items=request.maximum_items,
        )

        # 7. Safe Compression if overflow exists
        is_compressed = False
        if needs_compression and len(excluded) > 0:
            selected = ContextCompressor.compress_overflow(
                selected_items=selected,
                excluded_items=excluded,
                target_token_budget=request.maximum_tokens,
            )
            is_compressed = True
            token_est = sum(it.token_estimate for it in selected)

        # 8. Detect Context Conflicts
        conflicts = ContextConflictDetector.detect_conflicts(selected)

        # 9. Detect Missing Context
        missing = MissingContextDetector.detect_missing_context(request, selected)

        # 10. Quality Scoring
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        quality = ContextQualityEvaluator.evaluate_quality(
            selected_items=selected,
            total_candidates=len(candidates),
            build_latency_ms=elapsed_ms,
        )

        # 11. Compile Explanations and Partition Categories
        retrieval_reasons = {it.item_id: it.reason for it in selected}

        # Category partitions
        system_ctx = [
            it
            for it in selected
            if it.context_type in {UniversalContextType.TASK_CONTEXT, UniversalContextType.SESSION_CONTEXT}
        ]
        user_ctx = [it for it in selected if it.context_type == UniversalContextType.USER_CONTEXT]
        workspace_ctx = [it for it in selected if it.context_type == UniversalContextType.WORKSPACE_CONTEXT]
        agent_ctx = [it for it in selected if it.context_type == UniversalContextType.AGENT_CONTEXT]
        env_ctx = [it for it in selected if it.context_type == UniversalContextType.ENVIRONMENT_CONTEXT]
        memories = [it for it in selected if it.context_type == UniversalContextType.MEMORY_CONTEXT]
        knowledge = [it for it in selected if it.context_type == UniversalContextType.KNOWLEDGE_CONTEXT]
        decisions = [it for it in selected if it.context_type == UniversalContextType.DECISION_CONTEXT]
        plans = [it for it in selected if it.context_type == UniversalContextType.PLAN_CONTEXT]
        incidents = [it for it in selected if it.context_type == UniversalContextType.INCIDENT_CONTEXT]
        procedures = [it for it in selected if it.context_type == UniversalContextType.PROCEDURAL_CONTEXT]

        # 12. Assemble ContextPackage
        package = ContextPackage(
            request_id=request.context_request_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            task=request.task_type or request.query,
            intent=request.intent,
            goal=request.goal_id,
            environment=request.environment,
            items=selected,
            system_context=system_ctx,
            user_context=user_ctx,
            workspace_context=workspace_ctx,
            agent_context=agent_ctx,
            environment_context=env_ctx,
            memories=memories,
            knowledge=knowledge,
            decisions=decisions,
            plans=plans,
            incidents=incidents,
            procedures=procedures,
            uncertainties=[c.reason for c in conflicts if c.resolution_status == "UNRESOLVED"],
            conflicts=conflicts,
            missing_context=missing,
            retrieval_reasons=retrieval_reasons,
            confidence=quality.confidence,
            quality_score=quality,
            token_estimate=token_est,
            is_compressed=is_compressed,
            created_at=datetime.now(UTC),
        )

        # 13. Create Snapshot
        self.snapshots.create_snapshot(package)

        # 14. Cache result
        self.cache.set(
            package=package,
            session_id=request.session_id,
            task_id=request.task_id,
            agent_id=request.agent_id,
            query=request.query,
        )

        return package
