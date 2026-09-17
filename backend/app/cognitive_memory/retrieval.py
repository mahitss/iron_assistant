"""Hybrid Memory Retrieval & Context Pack Assembly Engine (Task 103).

Provides:
- Scope-isolated search preventing cross-project or cross-tenant leakage.
- Multi-stage hybrid retrieval (structured metadata + temporal freshness + semantic score).
- Evidence-based ranking favoring verified provenance over unverified claims.
- Bounded MemoryContextPack construction for Decision, Planning, and Mission engines.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.cognitive_memory.domain import (
    CognitiveMemoryItem,
    ExperienceTrust,
    FreshnessState,
    MemoryApplicationRecord,
    MemoryConflict,
    MemoryContextPack,
    MemoryLifecycleState,
    MemoryScope,
    MemoryType,
    _now_utc,
    _uuid_hex,
)

logger = logging.getLogger("kairo.cognitive_memory.retrieval")


class HybridMemoryRetrievalEngine:
    """Executes scope-isolated hybrid retrieval and constructs bounded context packs."""

    @classmethod
    def search_memories(
        cls,
        memories: List[CognitiveMemoryItem],
        query: str,
        scope: MemoryScope = MemoryScope.PROJECT,
        scope_id: Optional[str] = None,
        memory_types: Optional[List[MemoryType]] = None,
        include_stale: bool = False,
        include_candidates: bool = True,
        min_confidence: float = 0.5,
        limit: int = 10,
    ) -> List[CognitiveMemoryItem]:
        """Performs multi-criteria filtered retrieval with strict scope isolation."""
        candidates: List[CognitiveMemoryItem] = []
        tokens = set(query.lower().split())

        for mem in memories:
            # 1. Strict Scope Isolation:
            # If memory is scoped to a specific project/user/mission, it MUST NOT leak to another
            if mem.scope != MemoryScope.GLOBAL:
                if mem.scope != scope:
                    continue
                if scope_id is not None and mem.scope_id != scope_id:
                    continue

            # 2. Lifecycle status filter
            if not include_candidates and mem.lifecycle_state not in (MemoryLifecycleState.ACTIVE, MemoryLifecycleState.CONSOLIDATED):
                if not (include_stale and mem.lifecycle_state == MemoryLifecycleState.STALE):
                    continue

            # 3. Freshness filter
            if not include_stale and mem.freshness in (FreshnessState.STALE, FreshnessState.EXPIRED):
                continue

            # 4. Type filter
            if memory_types and mem.memory_type not in memory_types:
                continue

            # 5. Minimum confidence threshold
            if mem.confidence < min_confidence:
                continue

            # 6. Content matching score
            mem_text = f"{mem.content} {' '.join(mem.related_entities)} {' '.join(mem.preconditions)}".lower()
            matching_tokens = sum(1 for t in tokens if t in mem_text)
            match_score = matching_tokens / max(1, len(tokens))

            # Bonus for high-trust sources
            trust_bonus = 0.15 if mem.trust_classification in (ExperienceTrust.USER_CONFIRMED, ExperienceTrust.WORLD_STATE_VERIFIED) else 0.0
            relevance = match_score + trust_bonus

            if match_score > 0 or not tokens:
                candidates.append((mem, relevance))

        # Sort by relevance desc, then confidence desc
        candidates.sort(key=lambda pair: (pair[1], pair[0].confidence, pair[0].importance), reverse=True)
        return [c[0] for c in candidates[:limit]]

    @classmethod
    def assemble_context_pack(
        cls,
        query: str,
        memories: List[CognitiveMemoryItem],
        conflicts: Optional[List[MemoryConflict]] = None,
        scope: MemoryScope = MemoryScope.PROJECT,
        scope_id: Optional[str] = None,
        max_items: int = 8,
    ) -> MemoryContextPack:
        """Constructs a bounded, structured memory context pack for consumption by reasoning engines."""
        matched = cls.search_memories(
            memories=memories,
            query=query,
            scope=scope,
            scope_id=scope_id,
            limit=max_items,
        )

        relevant_mem_list: List[Dict[str, Any]] = []
        verified_procs: List[Dict[str, Any]] = []
        exceptions: List[str] = []
        world_overrides: List[str] = []

        for m in matched:
            item_dict = {
                "memory_id": m.memory_id,
                "type": m.memory_type.value,
                "content": m.content,
                "confidence": m.confidence,
                "freshness": m.freshness.value,
                "trust": m.trust_classification.value,
                "version": m.version,
            }
            relevant_mem_list.append(item_dict)

            if m.memory_type == MemoryType.PROCEDURAL:
                verified_procs.append({
                    "procedure_id": m.memory_id,
                    "title": m.content,
                    "preconditions": m.preconditions,
                    "steps": m.procedure_steps,
                    "verification_criteria": m.verification_criteria,
                    "last_verified": m.last_verified_at or m.observed_at,
                })

            if m.exceptions:
                exceptions.extend(m.exceptions)

            if m.freshness == FreshnessState.STALE:
                world_overrides.append(f"Memory {m.memory_id} is STALE: superseded by current world observation.")

        # Identify active conflicts related to retrieved memories
        active_conflict_list: List[Dict[str, Any]] = []
        retrieved_ids = {m.memory_id for m in matched}
        if conflicts:
            for conf in conflicts:
                if conf.status == "ACTIVE" and (conf.memory_a_id in retrieved_ids or conf.memory_b_id in retrieved_ids):
                    active_conflict_list.append({
                        "conflict_id": conf.conflict_id,
                        "claim_a": conf.memory_a_claim,
                        "claim_b": conf.memory_b_claim,
                        "evidence": conf.evidence,
                    })

        pack = MemoryContextPack(
            pack_id=_uuid_hex("pack"),
            query=query,
            scope=scope,
            assembled_at=_now_utc(),
            relevant_memories=relevant_mem_list,
            verified_procedures=verified_procs,
            active_conflicts=active_conflict_list,
            known_exceptions=list(set(exceptions)),
            world_state_overrides=world_overrides,
            total_items=len(relevant_mem_list),
        )

        logger.info(
            "Assembled MemoryContextPack %s for query '%s' [Memories: %d, Procedures: %d, Conflicts: %d]",
            pack.pack_id, query, len(pack.relevant_memories), len(pack.verified_procedures), len(pack.active_conflicts)
        )
        return pack

    @classmethod
    def record_application(
        cls,
        memory: CognitiveMemoryItem,
        consumer: str,
        context_summary: str,
        decision_ref: Optional[str] = None,
        action_ref: Optional[str] = None,
    ) -> MemoryApplicationRecord:
        """Records telemetry that a memory informed a specific decision or mission step."""
        memory.application_count += 1
        memory.access_count += 1

        rec = MemoryApplicationRecord(
            application_id=_uuid_hex("appl"),
            memory_id=memory.memory_id,
            consumer=consumer,
            context_summary=context_summary,
            applied_at=_now_utc(),
            decision_ref=decision_ref,
            action_ref=action_ref,
        )
        return rec
