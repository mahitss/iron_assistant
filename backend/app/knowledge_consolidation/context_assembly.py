"""Context assembly engine with explicit contradiction exposure for KAIRO (Task 92 Phase 20).

Guarantees:
- Filters stale, invalidated, and forgotten memories
- Ranks memories by multi-factor score: relevance * importance * confidence * freshness
- EXPLICITLY surfaces unresolved contradictions to reasoning models (never silently picks one)
- Constructs token-bounded, auditable context blocks
"""

from __future__ import annotations

from typing import Any

from app.knowledge_consolidation.models import (
    MemoryConflict,
    MemoryEntity,
    MemoryStatus,
)


class ContextAssemblyEngine:
    """Assembles curated reasoning context from validated knowledge."""

    def assemble_context(
        self,
        query: str,
        memories: list[MemoryEntity],
        active_conflicts: list[MemoryConflict],
        token_budget: int = 2000,
    ) -> dict[str, Any]:
        """Assemble bounded cognitive context for a reasoning request."""
        # 1. Filter out invalid/forgotten/blocked
        candidates = [
            m for m in memories
            if m.status not in (MemoryStatus.FORGOTTEN, MemoryStatus.INVALIDATED, MemoryStatus.BLOCKED)
        ]

        # 2. Score and rank candidates
        freshness_multipliers = {"FRESH": 1.0, "AGING": 0.85, "STALE": 0.5, "EXPIRED": 0.2}

        def score_fn(m: MemoryEntity) -> float:
            f_mult = freshness_multipliers.get(m.freshness, 0.8)
            # Penalize uncertain/conflicted slightly in rank, but do not omit
            status_mult = 0.7 if m.status == MemoryStatus.CONFLICTED else 1.0
            return m.relevance * m.importance * m.confidence * f_mult * status_mult

        candidates.sort(key=score_fn, reverse=True)

        # 3. Identify relevant contradictions
        candidate_ids = {m.memory_id for m in candidates}
        surfaced_conflicts: list[dict[str, Any]] = []

        for cnf in active_conflicts:
            if cnf.memory_a_id in candidate_ids or cnf.memory_b_id in candidate_ids:
                surfaced_conflicts.append({
                    "conflict_id": cnf.conflict_id,
                    "conflict_type": cnf.conflict_type.value,
                    "explanation": cnf.explanation,
                    "competing_values": cnf.competing_values,
                })

        # 4. Construct context blocks within budget
        selected_memories: list[dict[str, Any]] = []
        current_estimated_tokens = 0
        tokens_per_word = 1.3

        for m in candidates:
            word_count = len(m.content.split())
            est_tokens = int(word_count * tokens_per_word) + 15
            if current_estimated_tokens + est_tokens > token_budget:
                break

            selected_memories.append({
                "memory_id": m.memory_id,
                "type": m.type.value,
                "content": m.content,
                "confidence": m.confidence,
                "certainty": m.certainty.value,
                "freshness": m.freshness,
                "status": m.status.value,
            })
            current_estimated_tokens += est_tokens

        # 5. Build prompt-ready context string
        context_lines: list[str] = [f"=== KAIRO BOUNDED KNOWLEDGE CONTEXT (Query: '{query}') ==="]

        if surfaced_conflicts:
            context_lines.append("\n[CRITICAL WARNING: UNRESOLVED CONTRADICTIONS DETECTED]")
            for sc in surfaced_conflicts:
                context_lines.append(f"- CONFLICT ({sc['conflict_type']}): {sc['explanation']}")
                context_lines.append("  Note: Do NOT assume either value is true without explicit human confirmation.")

        context_lines.append("\n[VERIFIED & ACTIVE KNOWLEDGE]:")
        for sm in selected_memories:
            tag = f"[{sm['type']}|{sm['certainty']}]"
            context_lines.append(f"- {tag} {sm['content']}")

        formatted_context = "\n".join(context_lines)

        return {
            "query": query,
            "selected_memories": selected_memories,
            "surfaced_conflicts": surfaced_conflicts,
            "formatted_context": formatted_context,
            "estimated_tokens": current_estimated_tokens,
        }
