"""In-memory cosine similarity vector index with attribute filtering."""

import math
from typing import Any

from app.knowledge.schemas import DocumentChunk, RAGSourceType, TrustTier


class VectorIndex:
    """Vector similarity search index storing normalized embeddings with metadata filters."""

    def __init__(self) -> None:
        self._vectors: dict[str, list[float]] = {}
        self._chunks: dict[str, DocumentChunk] = {}

    def index_chunk(self, chunk: DocumentChunk, vector: list[float]) -> None:
        """Store chunk and its embedding."""
        # Normalize vector for cosine distance via dot product
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        normalized = [x / norm for x in vector]
        self._vectors[chunk.id] = normalized
        self._chunks[chunk.id] = chunk

    def remove_chunk(self, chunk_id: str) -> None:
        """Remove chunk from vector index."""
        self._vectors.pop(chunk_id, None)
        self._chunks.pop(chunk_id, None)

    def search(
        self,
        query_vector: list[float],
        limit: int = 50,
        user_id: str | None = None,
        project_id: str | None = None,
        allowed_sources: set[RAGSourceType] | None = None,
        min_trust_tier: TrustTier | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Perform cosine similarity vector search with metadata filtering."""
        if not self._vectors:
            return []

        # Normalize query vector
        q_norm = math.sqrt(sum(x * x for x in query_vector)) or 1.0
        norm_q = [x / q_norm for x in query_vector]

        results: list[tuple[DocumentChunk, float]] = []

        for chunk_id, vec in self._vectors.items():
            chunk = self._chunks.get(chunk_id)
            if not chunk:
                continue

            meta = chunk.metadata

            # Metadata filtering
            if user_id and meta.user_id != user_id and meta.user_id != "system":
                continue
            if project_id and meta.project_id and meta.project_id != project_id:
                continue
            if allowed_sources and meta.source_type not in allowed_sources:
                continue

            # Cosine similarity (dot product of unit vectors)
            sim = sum(a * b for a, b in zip(norm_q, vec, strict=False))
            results.append((chunk, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def total_vectors(self) -> int:
        return len(self._vectors)

    def clear(self) -> None:
        self._vectors.clear()
        self._chunks.clear()
