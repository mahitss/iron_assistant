"""ContextBudgeter: Token budgeting and 7-tier context hierarchy allocation (Task 69)."""

import logging

from app.context.universal_schemas import (
    ContextHierarchyLevel,
    ContextPriorityTier,
    UniversalContextItem,
)

logger = logging.getLogger("kairo.context.budgeting")


class ContextBudgeter:
    """Enforces token bounds, maximum items, and 7-tier hierarchy allocation."""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimate based on word and character counts."""
        if not text:
            return 0
        words = len(text.split())
        chars = len(text)
        return max(1, int(max(words * 1.3, chars / 4.0)))

    @classmethod
    def allocate_budget(
        cls,
        ranked_items: list[UniversalContextItem],
        max_tokens: int = 4000,
        max_items: int = 30,
    ) -> tuple[list[UniversalContextItem], list[UniversalContextItem], int, bool]:
        """Select highest value context items under token and item budget constraints.

        Returns: (selected_items, excluded_items, total_tokens, requires_compression)
        """
        # Assign estimated tokens to each item
        annotated: list[UniversalContextItem] = []
        for item in ranked_items:
            tok = cls.estimate_tokens(f"{item.title}\n{item.content}")
            annotated.append(item.model_copy(update={"token_estimate": tok}))

        # Priority order by hierarchy level and priority tier
        hierarchy_weights = {
            ContextHierarchyLevel.LEVEL_0_TASK: 7,
            ContextHierarchyLevel.LEVEL_1_SESSION: 6,
            ContextHierarchyLevel.LEVEL_2_USER_WORKSPACE: 5,
            ContextHierarchyLevel.LEVEL_3_GOALS: 4,
            ContextHierarchyLevel.LEVEL_4_RECENT_HISTORY: 3,
            ContextHierarchyLevel.LEVEL_5_LONG_TERM_MEMORY: 2,
            ContextHierarchyLevel.LEVEL_6_GENERAL_KNOWLEDGE: 1,
        }
        tier_weights = {
            ContextPriorityTier.CRITICAL: 10,
            ContextPriorityTier.HIGH: 5,
            ContextPriorityTier.NORMAL: 2,
            ContextPriorityTier.LOW: 0,
        }

        # Sort items taking relevance, tier, and hierarchy into account
        annotated.sort(
            key=lambda x: (
                tier_weights.get(x.priority_tier, 0),
                hierarchy_weights.get(x.hierarchy_level, 1),
                x.relevance_score,
            ),
            reverse=True,
        )

        selected: list[UniversalContextItem] = []
        excluded: list[UniversalContextItem] = []
        accumulated_tokens = 0

        for item in annotated:
            # Check if adding this item would exceed token or item limits
            if len(selected) >= max_items:
                excluded.append(item)
                continue

            if accumulated_tokens + item.token_estimate > max_tokens:
                # If it's CRITICAL and we have no items yet, take it anyway
                if item.priority_tier == ContextPriorityTier.CRITICAL and not selected:
                    selected.append(item)
                    accumulated_tokens += item.token_estimate
                else:
                    excluded.append(item)
            else:
                selected.append(item)
                accumulated_tokens += item.token_estimate

        requires_compression = len(excluded) > 0 and any(e.relevance_score > 0.6 for e in excluded)
        return selected, excluded, accumulated_tokens, requires_compression
