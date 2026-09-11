"""ContextRelevanceEngine: Multi-factor scoring and explainable ranking (Task 69)."""

import logging

from app.context.universal_schemas import ContextRequest, UniversalContextItem

logger = logging.getLogger("kairo.context.relevance")


class ContextRelevanceEngine:
    """Calculates multi-factor relevance scores and transparent inclusion rationales."""

    WEIGHT_SEMANTIC = 0.35
    WEIGHT_TASK_ALIGNMENT = 0.25
    WEIGHT_FRESHNESS = 0.15
    WEIGHT_TRUST_CONFIDENCE = 0.15
    WEIGHT_IMPORTANCE = 0.10

    PENALTY_ENV_MISMATCH = 0.35
    PENALTY_STALENESS = 0.25

    @classmethod
    def score_candidate(
        cls,
        item: UniversalContextItem,
        request: ContextRequest,
        known_query_terms: set[str] | None = None,
    ) -> tuple[float, str]:
        """Compute composite relevance score and explainable rationale for a candidate."""
        reasons: list[str] = []
        base_score = item.relevance_score

        # 1. Semantic and keyword overlap
        query_words = known_query_terms or set(request.query.lower().split())
        content_words = set(item.content.lower().split()).union(set(item.title.lower().split()))
        overlap = query_words.intersection(content_words)
        if overlap:
            semantic_boost = min(0.30, len(overlap) * 0.08)
            base_score += semantic_boost
            reasons.append(f"Keyword match on {list(overlap)[:3]}")

        # 2. Task / Intent alignment
        if request.intent and request.intent.lower() in item.content.lower():
            base_score += cls.WEIGHT_TASK_ALIGNMENT
            reasons.append(f"Matches active intent '{request.intent}'")

        # 3. Freshness & Recency
        freshness_factor = item.freshness_score
        if freshness_factor < 0.5:
            base_score -= cls.PENALTY_STALENESS
            reasons.append("Staleness penalty applied (-0.25)")
        else:
            base_score += cls.WEIGHT_FRESHNESS * freshness_factor
            reasons.append(f"Freshness boost ({freshness_factor:.2f})")

        # 4. Environment Alignment
        if item.environment:
            if item.environment.lower() == request.environment.lower():
                base_score += 0.15
                reasons.append(f"Direct environment match '{request.environment}'")
            else:
                base_score -= cls.PENALTY_ENV_MISMATCH
                reasons.append(f"Environment mismatch ({item.environment} vs {request.environment})")

        # 5. Trust and Confidence scaling
        trust_weight = 1.0 if item.trust_level in {"VERIFIED", "TRUSTED"} else 0.8
        conf_factor = item.confidence * trust_weight
        base_score = base_score * max(0.2, min(1.0, conf_factor))
        reasons.append(f"Trust/confidence weighted ({conf_factor:.2f})")

        # 6. Priority Tier Boost
        if item.priority_tier == "CRITICAL":
            base_score += 0.25
            reasons.append("Critical priority tier boost (+0.25)")
        elif item.priority_tier == "HIGH":
            base_score += 0.10

        final_score = round(max(0.01, min(1.0, base_score)), 4)
        explanation = "; ".join(reasons) if reasons else "General semantic relevance"

        return final_score, explanation

    @classmethod
    def rank_items(
        cls,
        items: list[UniversalContextItem],
        request: ContextRequest,
    ) -> list[UniversalContextItem]:
        """Score and sort items descending by final multi-factor relevance."""
        query_terms = set(request.query.lower().split())
        scored: list[tuple[float, UniversalContextItem]] = []

        for item in items:
            score, explanation = cls.score_candidate(item, request, query_terms)
            updated_item = item.model_copy(
                update={
                    "relevance_score": score,
                    "reason": explanation,
                }
            )
            scored.append((score, updated_item))

        # Sort descending by score, then priority tier, then timestamp
        tier_weights = {"CRITICAL": 4, "HIGH": 3, "NORMAL": 2, "LOW": 1}
        scored.sort(
            key=lambda x: (
                x[0],
                tier_weights.get(x[1].priority_tier.value, 1),
                x[1].timestamp or x[1].item_id,
            ),
            reverse=True,
        )

        return [item for _, item in scored]
