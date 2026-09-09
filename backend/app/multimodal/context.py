"""Structured Multimodal Context Packet builder and bounded token budgeting (Specs 33-35, 96)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.multimodal.limits import MultimodalLimits
from app.multimodal.schemas import (
    ModalityType,
    MultimodalEvidenceItem,
    MultimodalRequest,
    MultimodalResult,
)


@dataclass
class MultimodalContextPacket:
    """Bounded, compact context packet prepared for the ModelRouter and Context Engine."""

    request_id: str
    user_id: str
    project_id: str | None = None
    query_text: str = ""
    document_evidence: list[MultimodalEvidenceItem] = field(default_factory=list)
    image_evidence: list[MultimodalEvidenceItem] = field(default_factory=list)
    audio_transcripts: list[MultimodalEvidenceItem] = field(default_factory=list)
    video_keyframes: list[MultimodalEvidenceItem] = field(default_factory=list)
    screen_context: list[MultimodalEvidenceItem] = field(default_factory=list)
    total_token_estimate: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_system_prompt_block(self) -> str:
        """Serialize grounded multimodal context into clean, isolated prompt blocks."""
        sections = []

        if self.query_text:
            sections.append(f"User Inquiry:\n{self.query_text}")

        if self.screen_context:
            sections.append("### Authorized Screen Context Observation:")
            for sc in self.screen_context:
                sections.append(f"- [{sc.identifier}] {sc.content}")

        if self.document_evidence:
            sections.append("### Grounded Document Evidence:")
            for doc in self.document_evidence:
                page_info = f" (Page {doc.page})" if doc.page else ""
                sections.append(f"- [{doc.identifier}{page_info}]:\n{doc.content}")

        if self.image_evidence:
            sections.append("### Visual Inspection Evidence:")
            for img in self.image_evidence:
                sections.append(f"- [{img.identifier}]:\n{img.content}")

        if self.audio_transcripts:
            sections.append("### Audio Transcript Segments:")
            for aud in self.audio_transcripts:
                ts_info = f" ({aud.timestamp})" if aud.timestamp else ""
                sections.append(f"- [{aud.identifier}{ts_info}]: {aud.content}")

        if self.video_keyframes:
            sections.append("### Video Keyframe Moments:")
            for vid in self.video_keyframes:
                ts_info = f" ({vid.timestamp})" if vid.timestamp else ""
                sections.append(f"- [{vid.identifier}{ts_info}]: {vid.content}")

        return "\n\n".join(sections)


class MultimodalContextBuilder:
    """Assembles MultimodalContextPacket respecting configured token and item budgets."""

    def __init__(self, limits: MultimodalLimits | None = None) -> None:
        self.limits = limits or MultimodalLimits.load_from_settings()

    def build_packet(
        self,
        request: MultimodalRequest,
        results: list[MultimodalResult],
    ) -> MultimodalContextPacket:
        """Assemble results into a budget-bounded MultimodalContextPacket."""
        packet = MultimodalContextPacket(
            request_id=request.request_id,
            user_id=request.user_id,
            project_id=request.project_id,
            query_text=request.text or "",
        )

        # Collect evidence across results
        for res in results:
            for item in res.evidence:
                if item.source_type == ModalityType.DOCUMENT:
                    if len(packet.document_evidence) < self.limits.max_document_chunks:
                        packet.document_evidence.append(item)
                elif item.source_type == ModalityType.IMAGE:
                    if len(packet.image_evidence) < self.limits.max_images_per_request:
                        packet.image_evidence.append(item)
                elif item.source_type == ModalityType.AUDIO:
                    packet.audio_transcripts.append(item)
                elif item.source_type == ModalityType.VIDEO:
                    if len(packet.video_keyframes) < self.limits.max_video_frames:
                        packet.video_keyframes.append(item)
                elif item.source_type == ModalityType.SCREEN:
                    packet.screen_context.append(item)

        # Approximate token size
        prompt_block = packet.to_system_prompt_block()
        packet.total_token_estimate = int(len(prompt_block) * 0.25)

        # Truncate if token budget exceeded (Spec 35)
        if packet.total_token_estimate > self.limits.max_context_tokens:
            # Shed oldest/excess document chunks first
            while (
                len(packet.document_evidence) > 2
                and packet.total_token_estimate > self.limits.max_context_tokens
            ):
                packet.document_evidence.pop()
                packet.total_token_estimate = int(len(packet.to_system_prompt_block()) * 0.25)

        return packet
