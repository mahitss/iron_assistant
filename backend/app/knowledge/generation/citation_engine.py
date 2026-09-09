"""Citation engine formatting context blocks and validating generated answers against source evidence."""

import logging
import re
from typing import Any

from app.knowledge.schemas import HallucinationReport, RetrievalResult

logger = logging.getLogger("kairo.knowledge.generation")


class CitationEngine:
    """Formats retrieved chunks into grounded generation prompts and verifies citation accuracy."""

    def format_context(
        self,
        results: list[RetrievalResult],
        max_tokens: int = 4000,
        include_metadata: bool = True,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Format retrieval results into structured context block with numbered citations."""
        if not results:
            return "", []

        context_blocks: list[str] = []
        citation_manifest: list[dict[str, Any]] = []

        # Rough token approximation: 1 token ~= 4 chars
        char_budget = max_tokens * 4
        current_chars = 0

        for idx, item in enumerate(results, start=1):
            chunk = item.chunk
            meta = chunk.metadata

            # Header info
            header_parts = [f"Source [{idx}]: {item.citation_label}"]
            if include_metadata:
                header_parts.append(f"Trust: {meta.trust_tier.value} | Freshness: {meta.freshness.value}")
                if meta.source_type:
                    header_parts.append(f"Type: {meta.source_type.value}")

            header_str = " | ".join(header_parts)
            block = f"--- {header_str} ---\n{chunk.content}\n"

            if current_chars + len(block) > char_budget:
                # Truncate content if needed
                remaining = char_budget - current_chars
                if remaining > 150:
                    truncated_content = chunk.content[: remaining - 80] + "\n...[truncated]..."
                    block = f"--- {header_str} ---\n{truncated_content}\n"
                    context_blocks.append(block)
                    citation_manifest.append({
                        "index": idx,
                        "chunk_id": chunk.id,
                        "citation_label": item.citation_label,
                        "citation_url": item.citation_url,
                        "line_range": item.line_range,
                        "time_range": item.time_range,
                    })
                break

            context_blocks.append(block)
            current_chars += len(block)
            citation_manifest.append({
                "index": idx,
                "chunk_id": chunk.id,
                "citation_label": item.citation_label,
                "citation_url": item.citation_url,
                "line_range": item.line_range,
                "time_range": item.time_range,
            })

        full_context = "\n".join(context_blocks)
        return full_context, citation_manifest

    def verify_generation(
        self,
        generated_text: str,
        citation_manifest: list[dict[str, Any]],
        results: list[RetrievalResult],
    ) -> HallucinationReport:
        """Analyze generated answer, verify citation markers, and detect ungrounded factual assertions."""
        # Find citations in format [1], [2], etc.
        cited_indices = [int(m) for m in re.findall(r"\[(\d+)\]", generated_text)]
        manifest_indices = {m["index"] for m in citation_manifest}

        invalid_citations: list[str] = []
        for idx in cited_indices:
            if idx not in manifest_indices:
                invalid_citations.append(f"[{idx}] (does not exist in provided context)")

        # Map index to chunk content
        chunk_by_idx: dict[int, str] = {}
        for m in citation_manifest:
            idx = m["index"]
            # Find matching result
            matching = next((r for r in results if r.chunk.id == m["chunk_id"]), None)
            if matching:
                chunk_by_idx[idx] = matching.chunk.content.lower()

        sentences = re.split(r"(?<=[.!?])\s+", generated_text)
        ungrounded_claims: list[str] = []

        total_claims = 0
        grounded_claims = 0

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue

            cites = [int(m) for m in re.findall(r"\[(\d+)\]", sentence_clean)]
            if not cites:
                continue

            total_claims += 1
            # Check keywords in sentence against cited chunk content
            sentence_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", sentence_clean.lower()))
            # Remove common stopwords
            sentence_words -= {"with", "that", "this", "from", "have", "were", "what", "when", "where", "which"}

            claim_verified = False
            for c_idx in cites:
                if c_idx in chunk_by_idx:
                    chunk_text = chunk_by_idx[c_idx]
                    matches = sum(1 for w in sentence_words if w in chunk_text)
                    if matches >= min(2, len(sentence_words)):
                        claim_verified = True
                        break

            if claim_verified:
                grounded_claims += 1
            else:
                ungrounded_claims.append(sentence_clean)

        grounding_score = 1.0 if total_claims == 0 else (grounded_claims / total_claims)
        confidence_score = max(0.0, grounding_score - (0.2 * len(invalid_citations)))
        is_grounded = len(invalid_citations) == 0 and grounding_score >= 0.7

        return HallucinationReport(
            is_grounded=is_grounded,
            confidence_score=round(confidence_score, 3),
            grounding_score=round(grounding_score, 3),
            cited_indices=list(set(cited_indices)),
            invalid_citations=invalid_citations,
            ungrounded_claims=ungrounded_claims,
        )
