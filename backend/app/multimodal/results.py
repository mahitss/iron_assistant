"""Structured result formatting, grounded citations, and uncertainty declarations (Specs 59-63)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.multimodal.schemas import (
    Attachment,
    ModalityType,
    MultimodalErrorState,
    MultimodalEvidenceItem,
    MultimodalResult,
    MultimodalStatus,
)


class MultimodalResultBuilder:
    """Builder for constructing standardized MultimodalResult instances with citations and uncertainty."""

    def __init__(self, request_id: str, model_id: str = "kairo-multimodal-orchestrator") -> None:
        self.request_id = request_id
        self.model_id = model_id
        self.status: MultimodalStatus = MultimodalStatus.COMPLETED
        self.summary: str = ""
        self.evidence: list[MultimodalEvidenceItem] = []
        self.sources: list[str] = []
        self.artifacts: list[dict[str, Any]] = []
        self.modality_usage: dict[str, Any] = {}
        self.uncertainty_note: str | None = None
        self.error_code: MultimodalErrorState | None = None
        self.error_message: str | None = None

    def set_summary(self, summary: str) -> MultimodalResultBuilder:
        self.summary = summary
        return self

    def add_evidence(
        self,
        source_type: ModalityType,
        identifier: str,
        content: str,
        page: int | None = None,
        timestamp: str | None = None,
        region: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> MultimodalResultBuilder:
        """Add grounded evidence item. Confidence is model metadata, not factual certainty (Spec 62)."""
        self.evidence.append(
            MultimodalEvidenceItem(
                source_type=source_type,
                identifier=identifier,
                page=page,
                timestamp=timestamp,
                region=region,
                content=content,
                confidence=confidence,
            )
        )
        return self

    def add_source(self, source_citation: str) -> MultimodalResultBuilder:
        if source_citation not in self.sources:
            self.sources.append(source_citation)
        return self

    def set_uncertainty(self, note: str) -> MultimodalResultBuilder:
        """Declare that media was partially ambiguous, low-resolution, or unclear (Spec 63)."""
        self.uncertainty_note = note
        return self

    def set_error(self, code: MultimodalErrorState, message: str) -> MultimodalResultBuilder:
        self.status = MultimodalStatus.FAILED
        self.error_code = code
        self.error_message = message
        return self

    def set_usage(self, **kwargs: Any) -> MultimodalResultBuilder:
        self.modality_usage.update(kwargs)
        return self

    def build(self) -> MultimodalResult:
        return MultimodalResult(
            request_id=self.request_id,
            status=self.status,
            summary=self.summary,
            evidence=self.evidence,
            sources=self.sources,
            artifacts=self.artifacts,
            modality_usage=self.modality_usage,
            model=self.model_id,
            timestamp=datetime.now(UTC),
            uncertainty_note=self.uncertainty_note,
            error_code=self.error_code,
            error_message=self.error_message,
        )
