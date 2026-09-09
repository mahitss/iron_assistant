"""Retention policies, ephemeral vs durable memory, promotion rules, and decay (INVARIANTS 79-82, 111-113)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid


class RetentionManager:
    """Manages memory promotion from ephemeral candidates to durable memory and tracks decay."""

    def __init__(self) -> None:
        # candidate_id -> dict
        self._candidates: Dict[str, Dict[str, Any]] = {}
        # durable_id -> dict
        self._durable: Dict[str, Dict[str, Any]] = {}

    def register_candidate(
        self,
        content: str,
        memory_type: str,
        utility_score: float = 0.5,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """INVARIANT 79: Create memory candidates before durable persistence."""
        cid = str(uuid.uuid4())
        record = {
            "candidate_id": cid,
            "content": content,
            "memory_type": memory_type,
            "utility_score": utility_score,
            "repetition_count": 1,
            "verified": False,
            "created_at": datetime.now(UTC).isoformat(),
            "user_id": user_id,
        }
        self._candidates[cid] = record
        return record

    def promote_to_durable(
        self,
        candidate_id: str,
        is_verified: bool = False,
        explicit_user_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """INVARIANT 80: Promote candidate to durable memory based on verification or explicit confirmation."""
        cand = self._candidates.get(candidate_id)
        if not cand:
            raise ValueError(f"Candidate '{candidate_id}' not found.")

        if not is_verified and not explicit_user_confirmed and cand["utility_score"] < 0.75 and cand["repetition_count"] < 3:
            raise ValueError("Candidate does not meet criteria for durable promotion.")

        cand["is_durable"] = True
        cand["promoted_at"] = datetime.now(UTC).isoformat()
        self._durable[candidate_id] = cand
        return cand

    def apply_decay(self, candidate_id: str, decay_factor: float = 0.1) -> float:
        """INVARIANT 81: Memory relevance decay over time."""
        cand = self._candidates.get(candidate_id)
        if cand:
            cand["utility_score"] = max(cand["utility_score"] - decay_factor, 0.0)
            return cand["utility_score"]
        return 0.0

    def reinforce(self, candidate_id: str, boost: float = 0.15) -> float:
        """INVARIANT 82: Repeated verified use increases relevance."""
        cand = self._candidates.get(candidate_id)
        if cand:
            cand["repetition_count"] += 1
            cand["utility_score"] = min(cand["utility_score"] + boost, 1.0)
            return cand["utility_score"]
        return 0.0
