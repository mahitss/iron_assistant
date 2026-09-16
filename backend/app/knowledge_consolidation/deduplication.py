"""Semantic and structured deduplication engine for KAIRO knowledge (Task 92 Phase 7).

Guarantees:
- Detects exact duplicates, near-duplicates, and repeated observations
- Merges evidence and provenance rather than creating duplicate memory entries
- Preserves all provenance chains across merged sources
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.knowledge_consolidation.models import (
    EvidenceRelationType,
    MemoryEntity,
    ProvenanceSourceType,
)


def normalize_text(text: str) -> str:
    """Lowercase and strip whitespace/punctuation for canonical representation."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(cleaned.split())


def compute_content_hash(text: str, structured_payload: dict[str, Any] | None = None) -> str:
    """Compute deterministic SHA-256 hash over normalized content and core structured keys."""
    norm = normalize_text(text)
    payload_repr = str(sorted((structured_payload or {}).items()))
    combined = f"{norm}|{payload_repr}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def compute_token_jaccard(text_a: str, text_b: str) -> float:
    """Compute token-level Jaccard similarity coefficient between two strings."""
    tokens_a = set(normalize_text(text_a).split())
    tokens_b = set(normalize_text(text_b).split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


class DeduplicationEngine:
    """Handles exact and semantic duplicate detection and safe evidence merging."""

    def __init__(self, semantic_similarity_threshold: float = 0.85) -> None:
        self.threshold = semantic_similarity_threshold
        # hash -> memory_id
        self._exact_hash_index: dict[str, str] = {}

    def register_memory(self, memory: MemoryEntity) -> None:
        """Register memory in exact hash index."""
        chash = compute_content_hash(memory.content, memory.structured_representation)
        self._exact_hash_index[chash] = memory.memory_id

    def find_duplicate(
        self,
        candidate_content: str,
        candidate_structured: dict[str, Any] | None,
        existing_memories: list[MemoryEntity],
    ) -> tuple[MemoryEntity | None, str]:
        """Check for exact or semantic duplicates among active memories.

        Returns: (matched_memory, match_type) where match_type is 'EXACT', 'SEMANTIC', or 'NONE'.
        """
        chash = compute_content_hash(candidate_content, candidate_structured)

        # 1. Exact hash match
        if chash in self._exact_hash_index:
            target_id = self._exact_hash_index[chash]
            for m in existing_memories:
                if m.memory_id == target_id:
                    return m, "EXACT"

        # 2. Semantic token overlap match
        for m in existing_memories:
            similarity = compute_token_jaccard(candidate_content, m.content)
            if similarity >= self.threshold:
                return m, "SEMANTIC"

        return None, "NONE"

    def merge_into_existing(
        self,
        existing_memory: MemoryEntity,
        new_content: str,
        new_source: str,
        new_source_type: ProvenanceSourceType,
        evidence_manager: Any,
        new_confidence: float = 0.8,
    ) -> MemoryEntity:
        """Merge observation/evidence into existing memory, reinforcing and preserving provenance."""
        # Attach supporting evidence
        evidence_manager.attach_evidence(
            memory_id=existing_memory.memory_id,
            content=new_content,
            source=new_source,
            relation_type=EvidenceRelationType.SUPPORT,
            source_type=new_source_type,
            reliability=0.85,
            confidence=new_confidence,
            freshness="FRESH",
            verification_status="VERIFIED",
        )

        # Incrementally adjust confidence (calibrated, bounded <= 1.0)
        existing_memory.confidence = min(1.0, existing_memory.confidence + 0.05)
        existing_memory.relevance = max(existing_memory.relevance, 1.0)
        existing_memory.freshness = "FRESH"

        return existing_memory
