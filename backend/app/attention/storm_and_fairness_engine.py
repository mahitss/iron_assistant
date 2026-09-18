"""Attention Storm Mitigation, Fairness Aging & Starvation Prevention Engine (Task 109, Spec 26, 27, 32, 33, 45).

Guarantees:
- LOUD != IMPORTANT & MANY SIGNALS != MANY INDEPENDENT EVENTS
- Rapid burst / storm detection with automatic deduplication and rate limiting
- Aging boost on deferred candidates to prevent low-priority starvation
- Merging and splitting of attention candidates
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from app.attention.domain import (
    AttentionCandidate,
    AttentionLifecycleState,
    AttentionSuppression,
    CognitiveHealthStatus,
    gen_attn_id,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class StormAndFairnessEngine:
    """Detects attention floods, applies starvation prevention aging, and manages candidate deduplication."""

    STORM_BURST_THRESHOLD = 15  # > 15 candidates in 10 seconds triggers storm mitigation
    STORM_WINDOW_SEC = 10.0
    AGING_BOOST_PER_HOUR = 0.08  # Gradual salience boost to prevent indefinite starvation
    MAX_AGING_BOOST = 0.40  # Maximum aging boost allowable

    def __init__(self) -> None:
        self.ingestion_timestamps: List[datetime] = []
        self.suppressions: List[AttentionSuppression] = []
        self.seen_fingerprints: Dict[str, Tuple[str, datetime]] = {}  # fingerprint -> (candidate_id, ts)

    def record_ingestion(self) -> Tuple[bool, CognitiveHealthStatus, str]:
        """Tracks candidate ingestion rates and identifies attention storms (Spec 45)."""
        now = utc_now()
        self.ingestion_timestamps.append(now)
        # Purge timestamps outside the storm window
        self.ingestion_timestamps = [
            ts for ts in self.ingestion_timestamps
            if (now - ts).total_seconds() <= self.STORM_WINDOW_SEC
        ]

        count = len(self.ingestion_timestamps)
        if count >= self.STORM_BURST_THRESHOLD:
            return (
                True,
                CognitiveHealthStatus.ATTENTION_STORM,
                f"Attention Storm Detected: {count} events received in {self.STORM_WINDOW_SEC}s. Rate limiting applied.",
            )

        return False, CognitiveHealthStatus.HEALTHY, "Normal ingestion rate."

    def check_duplicate_or_suppress(
        self,
        candidate: AttentionCandidate,
        dedup_window_sec: float = 60.0,
    ) -> Tuple[bool, Optional[str]]:
        """Checks for duplicate or rapid re-triggering of identical candidates (Spec 32)."""
        now = utc_now()
        # Generate fingerprint based on source, type, and target
        fingerprint = f"{candidate.source}::{candidate.type}::{candidate.target}::{candidate.title.lower().strip()}"

        if fingerprint in self.seen_fingerprints:
            existing_id, prev_ts = self.seen_fingerprints[fingerprint]
            delta = (now - prev_ts).total_seconds()
            if delta <= dedup_window_sec:
                # Suppress duplicate
                suppression = AttentionSuppression(
                    candidate_id=candidate.candidate_id,
                    fingerprint=fingerprint,
                    reason=f"DUPLICATE of {existing_id} within {delta:.1f}s",
                    suppressed_at=now,
                )
                self.suppressions.append(suppression)
                candidate.lifecycle = AttentionLifecycleState.SUPPRESSED
                return True, f"Suppressed as duplicate of {existing_id} ({delta:.1f}s ago)"

        self.seen_fingerprints[fingerprint] = (candidate.candidate_id, now)
        return False, None

    def apply_fairness_aging(
        self,
        queue: List[AttentionCandidate],
        now: Optional[datetime] = None,
    ) -> List[AttentionCandidate]:
        """Applies aging boosts to deferred/queued candidates to prevent starvation (Spec 26)."""
        current_time = now or utc_now()
        for cand in queue:
            if cand.lifecycle in (AttentionLifecycleState.QUEUED, AttentionLifecycleState.DEFERRED):
                age_hours = cand.age_seconds / 3600.0
                # Deferral count also accelerates fairness
                deferral_factor = min(0.20, cand.deferral_count * 0.05)
                raw_boost = (age_hours * self.AGING_BOOST_PER_HOUR) + deferral_factor
                boost = min(self.MAX_AGING_BOOST, round(raw_boost, 4))

                cand.aging_boost = boost
                # Recompute composite salience with aging boost
                original_salience = cand.score.composite_salience
                effective_salience = min(1.0, round(original_salience + boost, 4))
                cand.score.composite_salience = effective_salience
                if boost > 0.05 and "Fairness aging boost" not in cand.score.explanation:
                    cand.score.contributing_factors.append(f"Fairness aging boost (+{boost:.2f})")
                    cand.score.explanation += f"; Fairness aging boost applied (+{boost:.2f})"

        return queue

    @classmethod
    def merge_candidates(
        cls,
        candidates: List[AttentionCandidate],
        merged_title: str,
        target: str = "merged_target",
    ) -> AttentionCandidate:
        """Merges a storm of correlated alerts into a single unified candidate (Spec 33)."""
        if not candidates:
            raise ValueError("Cannot merge empty candidate list")

        now = utc_now()
        highest_urgency = max(c.score.urgency for c in candidates)
        highest_risk = max(c.score.risk for c in candidates)
        combined_evidence = []
        for c in candidates:
            combined_evidence.extend(c.evidence_ids)

        merged = AttentionCandidate(
            candidate_id=gen_attn_id("amerg"),
            source="storm_consolidator",
            type=candidates[0].type,
            target=target,
            scope=candidates[0].scope,
            timestamp=now,
            title=merged_title,
            description=f"Consolidated storm of {len(candidates)} signals: " + "; ".join(c.title for c in candidates[:4]),
            evidence_ids=list(set(combined_evidence)),
        )
        merged.score.urgency = highest_urgency
        merged.score.risk = highest_risk
        merged.score.composite_salience = min(1.0, round(max(c.score.composite_salience for c in candidates) + 0.1, 4))
        merged.score.explanation = f"Merged {len(candidates)} related events to avoid cognitive storm."

        for c in candidates:
            c.lifecycle = AttentionLifecycleState.MERGED

        return merged
