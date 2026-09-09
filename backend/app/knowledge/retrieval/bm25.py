"""Okapi BM25 ranking algorithm with in-memory inverted index."""

import math
import re
from collections import Counter, defaultdict
from typing import Any

from app.knowledge.schemas import DocumentChunk


class BM25Index:
    """Okapi BM25 implementation for lexical keyword retrieval across document chunks."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._doc_lengths: dict[str, int] = {}
        self._avg_doc_len: float = 0.0
        self._doc_count: int = 0
        self._term_doc_frequencies: dict[str, int] = defaultdict(int)
        self._inverted_index: dict[str, dict[str, int]] = defaultdict(dict)  # term -> {doc_id: freq}
        self._chunk_map: dict[str, DocumentChunk] = {}

    def _tokenize(self, text: str) -> list[str]:
        # Simple fast alphanumeric tokenization, lowercased
        return re.findall(r"\b\w+\b", text.lower())

    def index_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Batch index document chunks."""
        for chunk in chunks:
            self.index_chunk(chunk)

    def index_chunk(self, chunk: DocumentChunk) -> None:
        """Index a single document chunk."""
        doc_id = chunk.id
        if doc_id in self._doc_lengths:
            self.remove_chunk(doc_id)

        tokens = self._tokenize(chunk.content)
        length = len(tokens)
        self._doc_lengths[doc_id] = length
        self._chunk_map[doc_id] = chunk

        # Count frequencies in this document
        tf = Counter(tokens)
        for term, freq in tf.items():
            self._inverted_index[term][doc_id] = freq
            self._term_doc_frequencies[term] += 1

        self._doc_count = len(self._doc_lengths)
        if self._doc_count > 0:
            self._avg_doc_len = sum(self._doc_lengths.values()) / self._doc_count

    def remove_chunk(self, doc_id: str) -> None:
        """Remove a document chunk from the index."""
        if doc_id not in self._doc_lengths:
            return

        del self._doc_lengths[doc_id]
        if doc_id in self._chunk_map:
            del self._chunk_map[doc_id]

        for term in list(self._inverted_index.keys()):
            if doc_id in self._inverted_index[term]:
                del self._inverted_index[term][doc_id]
                self._term_doc_frequencies[term] -= 1
                if self._term_doc_frequencies[term] <= 0:
                    del self._term_doc_frequencies[term]
                    del self._inverted_index[term]

        self._doc_count = len(self._doc_lengths)
        if self._doc_count > 0:
            self._avg_doc_len = sum(self._doc_lengths.values()) / self._doc_count
        else:
            self._avg_doc_len = 0.0

    def search(self, query: str, limit: int = 50) -> list[tuple[DocumentChunk, float]]:
        """Compute BM25 scores for a query across all indexed chunks."""
        if self._doc_count == 0:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        scores: dict[str, float] = defaultdict(float)

        for term in q_tokens:
            if term not in self._inverted_index:
                continue

            df = self._term_doc_frequencies[term]
            # Standard Lucene/BM25 IDF formula
            idf = math.log(1.0 + (self._doc_count - df + 0.5) / (df + 0.5))

            postings = self._inverted_index[term]
            for doc_id, freq in postings.items():
                doc_len = self._doc_lengths[doc_id]
                denom = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / (self._avg_doc_len or 1.0)))
                term_score = idf * (freq * (self.k1 + 1.0)) / (denom or 1.0)
                scores[doc_id] += term_score

        if not scores:
            return []

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [(self._chunk_map[doc_id], score) for doc_id, score in ranked if doc_id in self._chunk_map]

    def clear(self) -> None:
        self._doc_lengths.clear()
        self._avg_doc_len = 0.0
        self._doc_count = 0
        self._term_doc_frequencies.clear()
        self._inverted_index.clear()
        self._chunk_map.clear()
