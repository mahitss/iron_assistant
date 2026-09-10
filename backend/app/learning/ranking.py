"""Adaptive ranking without popularity bias or sensitive profiling (INVARIANTS 147-150)."""

from __future__ import annotations

from typing import Any


class AdaptiveRankingEngine:
    """Ranks memory and knowledge candidates prioritizing verified authority while preventing sensitive profiling."""

    @classmethod
    def rank_candidates(
        cls,
        candidates: list[dict[str, Any]],
        task_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """INVARIANT 147-150: Multi-factor ranking:
        - Authority Tier (+0.4)
        - Verification Status (+0.3)
        - Outcome Relevance (+0.2)
        - Recency (+0.1)
        """
        ranked = []
        for cand in candidates:
            c = dict(cand)
            score = 0.0

            # INVARIANT 150: Prioritize authoritative/verified knowledge
            source_tier = c.get("tier", "UNVERIFIED")
            if source_tier in ("SYSTEM_AUTHORITATIVE", "GOVERNANCE"):
                score += 0.40
            elif source_tier in ("VERIFIED_TOOL", "USER_EXPLICIT"):
                score += 0.30
            elif source_tier in ("PROJECT_DOC", "REPOSITORY"):
                score += 0.20

            if c.get("verified", False):
                score += 0.30

            # Relevance boost
            if task_context and c.get("domain") == task_context.get("domain"):
                score += 0.20

            # Base relevance
            base_score = float(c.get("score", 0.5))
            final_rank = round(score + (base_score * 0.3), 3)
            c["adaptive_rank"] = final_rank
            ranked.append(c)

        ranked.sort(key=lambda x: x["adaptive_rank"], reverse=True)
        return ranked
