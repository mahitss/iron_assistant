"""Relevance Engine for Task 110:
Multi-objective, transparent context relevance scoring with auditable component breakdowns.

Strict Invariants:
- HIGH RELEVANCE != HIGH TRUTH.
- Avoids opaque magic numbers; stores component scores separately.
- Configurable and versioned weightings.
- Pinned and safety-critical elements are elevated explicitly.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from app.context.working_set_domain import (
    ContextAssemblyRequest,
    ContextCandidate,
    ItemInclusionSemantics,
)


class RelevanceEngine:
    """Computes transparent, componentized relevance scores for context candidates."""

    VERSION = "1.0.0"

    # Default balanced weight matrix
    DEFAULT_WEIGHTS = {
        "task_alignment": 0.25,
        "attention_focus": 0.20,
        "semantic_similarity": 0.20,
        "temporal_freshness": 0.15,
        "dependency_causal": 0.10,
        "contradiction_uncertainty": 0.10,
    }

    @classmethod
    def score_candidate(
        cls,
        candidate: ContextCandidate,
        request: ContextAssemblyRequest,
        freshness_score: float = 1.0,
        has_conflict: bool = False,
        is_pinned: bool = False,
        is_required: bool = False,
        custom_weights: Dict[str, float] | None = None,
    ) -> Tuple[float, Dict[str, float], ItemInclusionSemantics]:
        """Compute composite relevance and determine initial inclusion semantics."""
        weights = custom_weights or cls.DEFAULT_WEIGHTS

        # 1. Task / Objective Alignment (Keyword & intent matching)
        objective_terms = set(re.findall(r"\w+", (request.objective + " " + (request.explicit_user_request or "")).lower()))
        content_terms = set(re.findall(r"\w+", (candidate.title + " " + candidate.raw_content[:500]).lower()))

        overlap = len(objective_terms.intersection(content_terms))
        task_score = min(1.0, (overlap / max(1, len(objective_terms))) * 1.5) if objective_terms else 0.5

        # 2. Attention Focus Alignment (Task 109)
        attn_score = candidate.preliminary_relevance if candidate.source_subsystem == "attention" else (0.8 if candidate.source_subsystem in ("intent", "missions") else 0.5)

        # 3. Semantic Similarity (normalized text overlap and preliminary relevance)
        semantic_score = candidate.preliminary_relevance

        # 4. Temporal Freshness (decay evaluated by FreshnessEngine)
        temporal_score = freshness_score

        # 5. Dependency & Causal Linkage
        dependency_score = 0.9 if candidate.dependencies else 0.5

        # 6. Contradiction & Uncertainty Relevance (conflicts must remain visible)
        contradiction_score = 1.0 if has_conflict else 0.3

        # Assemble component breakdown
        components = {
            "task_alignment": round(task_score, 4),
            "attention_focus": round(attn_score, 4),
            "semantic_similarity": round(semantic_score, 4),
            "temporal_freshness": round(temporal_score, 4),
            "dependency_causal": round(dependency_score, 4),
            "contradiction_uncertainty": round(contradiction_score, 4),
        }

        # Weighted composite calculation
        composite = sum(components[k] * weights.get(k, 0.1) for k in components)
        composite = round(min(1.0, max(0.0, composite)), 4)

        # Inclusion Semantics Determination
        if is_required:
            inclusion = ItemInclusionSemantics.REQUIRED
            composite = max(composite, 0.95)
        elif is_pinned or candidate.candidate_id in request.pinned_item_ids:
            inclusion = ItemInclusionSemantics.REQUIRED
            composite = max(composite, 0.90)
        elif has_conflict:
            inclusion = ItemInclusionSemantics.IMPORTANT
            composite = max(composite, 0.85)
        elif composite >= 0.70:
            inclusion = ItemInclusionSemantics.IMPORTANT
        elif composite >= 0.35:
            inclusion = ItemInclusionSemantics.OPTIONAL
        else:
            inclusion = ItemInclusionSemantics.EXCLUDED

        # Untrusted content never gains REQUIRED status automatically
        if candidate.is_untrusted and inclusion == ItemInclusionSemantics.REQUIRED and not is_pinned:
            inclusion = ItemInclusionSemantics.OPTIONAL

        return composite, components, inclusion
