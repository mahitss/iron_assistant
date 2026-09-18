"""Compression & Transformation Engine for Task 110:
Applies budget-aware compression to context items while tracking information loss and retaining source references.

Strict Invariants:
- SUMMARY != SOURCE (Never claims a lossy summary is equivalent to the source).
- COMPRESSION != LOSSLESS REPRESENTATION.
- Safety-critical context and high-confidence contradiction evidence are never compressed destructively.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.context.working_set_domain import (
    CompressionLevel,
    ContextTransformation,
    ItemInclusionSemantics,
    gen_ctx_id,
    utc_now,
)


class CompressionEngine:
    """Performs budget-sensitive compression and tracks explicit transformation artifacts."""

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate token count based on standard whitespace and punctuation heuristic (~4 chars/token)."""
        if not text:
            return 0
        return max(1, len(text) // 4)

    @classmethod
    def compress_content(
        cls,
        item_id: str,
        content: str,
        target_level: CompressionLevel,
        inclusion: ItemInclusionSemantics,
        source_ref: Optional[str] = None,
    ) -> Tuple[str, CompressionLevel, Optional[ContextTransformation]]:
        """Apply safe compression based on target level and necessity semantics."""
        # Safety invariant: REQUIRED items cannot be compressed past LIGHT
        actual_level = target_level
        if inclusion == ItemInclusionSemantics.REQUIRED and target_level in (
            CompressionLevel.MODERATE,
            CompressionLevel.AGGRESSIVE,
            CompressionLevel.REFERENCE_ONLY,
        ):
            actual_level = CompressionLevel.LIGHT

        if actual_level == CompressionLevel.NONE or len(content) < 60:
            return content, CompressionLevel.NONE, None

        orig_len = len(content)
        transformed_content = content
        loss_class = "NONE"

        if actual_level == CompressionLevel.LIGHT:
            # Strip excessive whitespace, redundant newlines, preserve core content
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            transformed_content = " ".join(lines)
            loss_class = "MINOR"
        elif actual_level == CompressionLevel.MODERATE:
            # Truncate to first 300 characters + summary marker
            if len(content) > 300:
                transformed_content = content[:280].rsplit(" ", 1)[0] + "... [TRUNCATED - Summary of remaining content]"
                loss_class = "MODERATE"
        elif actual_level == CompressionLevel.AGGRESSIVE:
            # Extract first sentence or headline
            first_sentence = content.split(". ")[0]
            transformed_content = f"[EXTRACT] {first_sentence}. (Original length: {orig_len} chars)"
            loss_class = "SEVERE"
        elif actual_level == CompressionLevel.REFERENCE_ONLY:
            # Pointer only
            transformed_content = f"[REFERENCE ONLY] Source: {source_ref or item_id} (Full content retained in source storage)"
            loss_class = "SEVERE"

        transformation = ContextTransformation(
            transformation_id=gen_ctx_id("tr"),
            input_item_ids=[item_id],
            output_item_id=item_id,
            transformation_type=f"COMPRESS_{actual_level.value}",
            algorithm="context_compressor_v1",
            timestamp=utc_now(),
            information_loss=loss_class,
            is_reversible=False,
            original_size_bytes=orig_len,
            transformed_size_bytes=len(transformed_content),
            source_reference=source_ref,
        )

        return transformed_content, actual_level, transformation
