"""ContextCompressor: Provenance-preserving context compression and clustering (Task 69)."""

import logging
from datetime import UTC, datetime

from app.context.universal_schemas import (
    ContextHierarchyLevel,
    ContextPriorityTier,
    UniversalContextItem,
    UniversalContextType,
)

logger = logging.getLogger("kairo.context.compression")


class ContextCompressor:
    """Safely compresses overflowing context into consolidated abstractions while preserving provenance DAG."""

    @classmethod
    def compress_overflow(
        cls,
        selected_items: list[UniversalContextItem],
        excluded_items: list[UniversalContextItem],
        target_token_budget: int = 4000,
    ) -> list[UniversalContextItem]:
        """Compress clusters of related excluded high-value items into summary representations."""
        # Find high-value excluded items (relevance >= 0.5)
        candidates = [it for it in excluded_items if it.relevance_score >= 0.5]
        if not candidates:
            return selected_items

        # Group by context_type
        by_type: dict[UniversalContextType, list[UniversalContextItem]] = {}
        for it in candidates:
            by_type.setdefault(it.context_type, []).append(it)

        compressed_items: list[UniversalContextItem] = list(selected_items)
        now = datetime.now(UTC)

        for c_type, cluster in by_type.items():
            if len(cluster) >= 2:
                # Synthesize a compressed summary item
                source_ids = [c.item_id for c in cluster]
                summary_text = f"Consolidated summary of {len(cluster)} {c_type.value} items: " + "; ".join(
                    f"[{c.title}: {c.content[:80]}]" for c in cluster[:3]
                )
                if len(cluster) > 3:
                    summary_text += f" ... (+{len(cluster) - 3} more items)"

                compressed_item = UniversalContextItem(
                    item_id=f"item_compressed_{c_type.value.lower()}_{int(now.timestamp())}",
                    context_type=c_type,
                    source_id=f"compressed_cluster_{len(cluster)}",
                    source_type="context_compression",
                    title=f"Compressed Summary ({len(cluster)} {c_type.value} items)",
                    content=summary_text,
                    hierarchy_level=ContextHierarchyLevel.LEVEL_4_RECENT_HISTORY,
                    priority_tier=ContextPriorityTier.NORMAL,
                    relevance_score=round(sum(c.relevance_score for c in cluster) / len(cluster), 4),
                    freshness_score=round(sum(c.freshness_score for c in cluster) / len(cluster), 2),
                    confidence=0.85,
                    trust_level="DERIVED_SUMMARY",
                    importance=0.6,
                    timestamp=now,
                    provenance=f"Synthesized from {len(cluster)} source items ({', '.join(source_ids[:4])})",
                    derived_from_ids=source_ids,
                    reason=f"Synthesized to fit within token budget ({target_token_budget} tokens)",
                    is_compressed=True,
                    token_estimate=max(1, len(summary_text.split()) * 2),
                )
                compressed_items.append(compressed_item)

        return compressed_items
