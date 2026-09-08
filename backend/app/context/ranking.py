"""Deterministic multi-factor context ranking and bounding engine."""

import math
from datetime import UTC, datetime

from app.context.schemas import ContextItem, ContextType


class ContextRanker:
    """Ranks and bounds candidate context items deterministically without black-box formulas."""

    WEIGHT_EXPLICIT_MENTION = 0.40
    WEIGHT_PROJECT_MATCH = 0.25
    WEIGHT_CONTINUITY = 0.20
    WEIGHT_RECENCY = 0.15

    @classmethod
    def compute_recency_score(cls, timestamp: datetime | None, now_dt: datetime | None = None) -> float:
        """Calculate exponential decay recency factor between 0.0 and 1.0 (half-life of 3 days)."""
        if not timestamp:
            return 0.20

        now = now_dt or datetime.now(UTC)
        if timestamp.tzinfo is None:
            # Assume UTC if naive
            ts = timestamp.replace(tzinfo=UTC)
        else:
            ts = timestamp.astimezone(UTC)

        age_hours = max(0.0, (now - ts).total_seconds() / 3600.0)
        # Half life of 72 hours (3 days)
        decay = math.exp(-age_hours / 72.0)
        return round(float(decay), 3)

    @classmethod
    def score_item(
        cls,
        item: ContextItem,
        user_query: str,
        active_project_id: str | None = None,
        query_terms: set[str] | None = None,
    ) -> float:
        """Compute aggregate relevance score for a context candidate."""
        score = item.relevance_score

        # 1. Explicit mention boost (e.g. title or content matched in query)
        q_lower = user_query.lower()
        if item.title.lower() in q_lower:
            score += cls.WEIGHT_EXPLICIT_MENTION
        elif query_terms:
            content_words = set(item.content.lower().split())
            shared = content_words.intersection(query_terms)
            if len(shared) >= 2:
                score += cls.WEIGHT_EXPLICIT_MENTION * 0.5

        # 2. Project match boost
        if active_project_id and item.source_type == ContextType.PROJECT_CONTEXT:
            score += cls.WEIGHT_PROJECT_MATCH

        # 3. Recency factor
        recency = cls.compute_recency_score(item.timestamp)
        score += cls.WEIGHT_RECENCY * recency

        # 4. Confidence scaling if applicable
        if item.confidence is not None:
            score = score * min(1.0, max(0.2, item.confidence))

        return round(score, 4)

    @classmethod
    def rank_and_bound(
        cls,
        items: list[ContextItem],
        max_total: int = 30,
        max_memories: int = 10,
        max_project_items: int = 10,
    ) -> list[ContextItem]:
        """Sort items descending by score and bound per-category and total budgets."""
        # Sort by relevance score descending, then by timestamp descending
        sorted_items = sorted(
            items,
            key=lambda x: (x.relevance_score, x.timestamp or datetime.min.replace(tzinfo=UTC)),
            reverse=True,
        )

        bounded: list[ContextItem] = []
        memory_count = 0
        project_count = 0

        for item in sorted_items:
            if len(bounded) >= max_total:
                break

            if item.source_type == ContextType.MEMORY_CONTEXT:
                if memory_count >= max_memories:
                    continue
                memory_count += 1

            elif item.source_type == ContextType.PROJECT_CONTEXT:
                if project_count >= max_project_items:
                    continue
                project_count += 1

            bounded.append(item)

        return bounded
