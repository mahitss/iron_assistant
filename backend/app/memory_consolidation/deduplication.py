"""Deduplication engine for Task 68: Kairo Autonomous Knowledge & Memory Consolidation Engine.

Enforces:
- Spec 8: Multi-tier duplicate detection (exact, near, semantic)
- Invariant: repetition != independent evidence
- Preservation of historical observation references when canonicalizing
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from app.memory_consolidation.schemas import DurableMemory

logger = logging.getLogger("kairo.memory_consolidation.deduplication")


class DeduplicationEngine:
    """Detects and canonicalizes duplicate memories while retaining independent provenance."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Strip punctuation and normalize whitespace for robust duplicate hashing."""
        clean = re.sub(r"[^\w\s]", "", text.lower())
        return " ".join(clean.split())

    @classmethod
    def compute_content_hash(cls, text: str) -> str:
        """Compute deterministic SHA-256 hash of normalized text."""
        norm = cls.normalize_text(text)
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    @classmethod
    def compute_token_similarity(cls, text_a: str, text_b: str) -> float:
        """Calculate Jaccard similarity over word tokens."""
        tokens_a = set(cls.normalize_text(text_a).split())
        tokens_b = set(cls.normalize_text(text_b).split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = len(tokens_a & tokens_b)
        union = len(tokens_a | tokens_b)
        return intersection / union if union > 0 else 0.0

    @classmethod
    def find_duplicate(
        cls,
        candidate_content: str,
        existing_memories: list[DurableMemory],
        similarity_threshold: float = 0.65,
    ) -> tuple[DurableMemory | None, float, str]:
        """Identify if a candidate memory is an exact or near duplicate (Spec 8)."""
        candidate_hash = cls.compute_content_hash(candidate_content)

        # 1. Exact hash match
        for mem in existing_memories:
            if cls.compute_content_hash(mem.content) == candidate_hash:
                return mem, 1.0, "EXACT_HASH_MATCH"

        # 2. Near duplicate token match
        best_match: DurableMemory | None = None
        best_score = 0.0
        for mem in existing_memories:
            score = cls.compute_token_similarity(candidate_content, mem.content)
            if score > best_score:
                best_score = score
                best_match = mem

        if best_match is not None and best_score >= similarity_threshold:
            return best_match, best_score, "NEAR_DUPLICATE_SIMILARITY"

        return None, best_score, "NO_DUPLICATE"

    @classmethod
    def merge_references_into_canonical(
        cls,
        canonical: DurableMemory,
        duplicate_source_ref: str,
        is_independent_source: bool = False,
    ) -> dict[str, Any]:
        """Link incoming duplicate observation to canonical memory without falsely inflating truth confidence (Spec 8)."""
        if duplicate_source_ref and duplicate_source_ref not in canonical.provenance.source_refs:
            canonical.provenance.source_refs.append(duplicate_source_ref)

        # Invariant: Simple repetition does not prove truth.
        # Only independent source confirmation slightly reinforces confidence (capped).
        if is_independent_source:
            canonical.confidence = min(canonical.confidence + 0.02, 1.0)
        else:
            logger.info("Repetition detected from dependent/correlated source: confidence unchanged.")

        return {
            "canonical_memory_id": canonical.memory_id,
            "merged_source_ref": duplicate_source_ref,
            "is_independent": is_independent_source,
            "new_confidence": canonical.confidence,
        }
