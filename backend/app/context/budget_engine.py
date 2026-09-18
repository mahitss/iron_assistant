"""Context Budget Engine for Task 110:
Manages token, byte, item, and latency budgets, enforcing graceful degradation ladders under resource pressure.

Strict Invariants:
- Integrates with Task 77 Resource Economy (does not usurp resource allocation authority).
- Never silently drops required safety context.
- Records explicit ContextGap records when budget exhaustion prevents critical inclusions.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.context.compression_engine import CompressionEngine
from app.context.working_set_domain import (
    CompressionLevel,
    ContextBudget,
    ContextExclusion,
    ContextGap,
    ContextItem,
    ContextTransformation,
    ItemInclusionSemantics,
    gen_ctx_id,
    utc_now,
)


class BudgetEngine:
    """Enforces token, item, and byte budgets across working set candidates."""

    @classmethod
    def apply_budget(
        cls,
        items: List[ContextItem],
        budget: ContextBudget,
    ) -> Tuple[List[ContextItem], List[ContextExclusion], List[ContextGap], List[ContextTransformation]]:
        """Fit candidate items into the allocated budget via the graceful degradation ladder."""
        included_items: List[ContextItem] = []
        exclusions: List[ContextExclusion] = []
        gaps: List[ContextGap] = []
        transformations: List[ContextTransformation] = []

        total_tokens = 0
        total_bytes = 0

        # Sort items strictly by degradation priority:
        # 1. REQUIRED (safety / system critical / user-pinned)
        # 2. IMPORTANT (conflicts, active task state)
        # 3. OPTIONAL (sorted by relevance descending)
        # 4. REFERENCE_ONLY
        def sort_key(item: ContextItem) -> Tuple[int, float]:
            priority_tier = 3
            if item.inclusion == ItemInclusionSemantics.REQUIRED:
                priority_tier = 0
            elif item.is_pinned:
                priority_tier = 0
            elif item.inclusion == ItemInclusionSemantics.IMPORTANT:
                priority_tier = 1
            elif item.inclusion == ItemInclusionSemantics.OPTIONAL:
                priority_tier = 2
            return (priority_tier, -item.relevance_score)

        sorted_items = sorted(items, key=sort_key)

        for item in sorted_items:
            item_tokens = item.token_estimate
            item_bytes = len(item.content.encode("utf-8"))

            # Check if including this item exceeds the hard budget
            if (total_tokens + item_tokens <= budget.max_tokens) and (len(included_items) < budget.max_items):
                included_items.append(item)
                total_tokens += item_tokens
                total_bytes += item_bytes
            else:
                # Budget pressure triggered!
                budget.is_exhausted = True

                if item.inclusion == ItemInclusionSemantics.REQUIRED or item.is_pinned:
                    # REQUIRED items MUST NOT be dropped: attempt LIGHT compression first
                    compressed_content, level, tr = CompressionEngine.compress_content(
                        item_id=item.item_id,
                        content=item.content,
                        target_level=CompressionLevel.LIGHT,
                        inclusion=item.inclusion,
                        source_ref=item.provenance.source_id,
                    )
                    new_tokens = CompressionEngine.estimate_tokens(compressed_content)
                    item.content = compressed_content
                    item.token_estimate = new_tokens
                    item.compression = level
                    if tr:
                        transformations.append(tr)

                    included_items.append(item)
                    total_tokens += new_tokens
                    total_bytes += len(compressed_content.encode("utf-8"))
                elif item.inclusion == ItemInclusionSemantics.IMPORTANT:
                    # IMPORTANT items: attempt MODERATE or AGGRESSIVE compression to fit
                    remaining_tokens = budget.max_tokens - total_tokens
                    if remaining_tokens > 40:
                        target_lvl = CompressionLevel.MODERATE if remaining_tokens > 80 else CompressionLevel.AGGRESSIVE
                        compressed_content, level, tr = CompressionEngine.compress_content(
                            item_id=item.item_id,
                            content=item.content,
                            target_level=target_lvl,
                            inclusion=item.inclusion,
                            source_ref=item.provenance.source_id,
                        )
                        new_tokens = CompressionEngine.estimate_tokens(compressed_content)
                        item.content = compressed_content
                        item.token_estimate = new_tokens
                        item.compression = level
                        if tr:
                            transformations.append(tr)

                        included_items.append(item)
                        total_tokens += new_tokens
                        total_bytes += len(compressed_content.encode("utf-8"))
                    else:
                        # Cannot fit even with compression: exclude and record gap
                        exclusions.append(
                            ContextExclusion(
                                candidate_id=item.item_id,
                                source_subsystem=item.provenance.source_type,
                                reason="BUDGET_EXHAUSTED",
                                relevance_score=item.relevance_score,
                                timestamp=utc_now(),
                            )
                        )
                        gaps.append(
                            ContextGap(
                                missing_information=f"Excluded important context: {item.title}",
                                why_it_matters=f"High-relevance ({item.relevance_score}) item excluded due to token budget ceiling ({budget.max_tokens})",
                                expected_source=item.provenance.source_type,
                                severity="HIGH",
                                is_blocking=False,
                                confidence_impact=0.15,
                            )
                        )
                else:
                    # OPTIONAL item: drop and record exclusion
                    exclusions.append(
                        ContextExclusion(
                            candidate_id=item.item_id,
                            source_subsystem=item.provenance.source_type,
                            reason="BUDGET_EXHAUSTED",
                            relevance_score=item.relevance_score,
                            timestamp=utc_now(),
                        )
                    )

        # Update budget telemetry
        budget.used_tokens = total_tokens
        budget.used_bytes = total_bytes
        budget.used_items = len(included_items)
        if budget.is_exhausted and not budget.exhaustion_reason:
            budget.exhaustion_reason = f"Exceeded max tokens ({budget.max_tokens}) or items ({budget.max_items})"

        return included_items, exclusions, gaps, transformations
