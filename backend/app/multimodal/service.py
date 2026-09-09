"""Unified Multimodal Orchestration Service (Specs 1, 28, 59, 69, 70)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.config.settings import get_settings
from app.models.registry import create_default_registry
from app.multimodal.context import MultimodalContextBuilder, MultimodalContextPacket
from app.multimodal.events import MultimodalEventPublisher
from app.multimodal.limits import MultimodalLimitExceededError, MultimodalLimits
from app.multimodal.normalizer import MediaNormalizer
from app.multimodal.processors.audio import AudioProcessor
from app.multimodal.processors.document import DocumentProcessor
from app.multimodal.processors.image import ImageProcessor
from app.multimodal.processors.screen import ScreenProcessor
from app.multimodal.processors.video import VideoProcessor
from app.multimodal.results import MultimodalResultBuilder
from app.multimodal.router import MultimodalModelRouter, MultimodalRoutingError
from app.multimodal.schemas import (
    Attachment,
    AudioContext,
    ModalityType,
    MultimodalErrorState,
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
    ScreenContext,
)
from app.multimodal.security import (
    MultimodalSecurityError,
    MultimodalSecurityGate,
    PrivilegedModalityPermission,
)
from app.multimodal.validator import MediaValidator, MultimodalValidationError

logger = logging.getLogger("kairo.multimodal.service")


class MultimodalService:
    """Coordinates unified ingestion, validation, security, routing, and processing across all modalities."""

    def __init__(
        self,
        limits: MultimodalLimits | None = None,
        router: MultimodalModelRouter | None = None,
    ) -> None:
        self.limits = limits or MultimodalLimits.load_from_settings()
        self.validator = MediaValidator(self.limits)
        self.security = MultimodalSecurityGate()
        self.router = router or MultimodalModelRouter(create_default_registry())
        self.events = MultimodalEventPublisher()
        self.context_builder = MultimodalContextBuilder(self.limits)

        # Processors
        self.image_processor = ImageProcessor(self.limits)
        self.audio_processor = AudioProcessor(self.limits)
        self.video_processor = VideoProcessor(self.limits)
        self.document_processor = DocumentProcessor(self.limits)
        self.screen_processor = ScreenProcessor(self.limits)

        # User-scoped in-memory cache for safe derived artifacts (Spec 69, 70)
        self._cache: dict[str, MultimodalResult] = {}

    async def execute_request(self, request: MultimodalRequest) -> MultimodalResult:
        """Process a unified MultimodalRequest end-to-end through the authoritative pipeline."""
        builder = MultimodalResultBuilder(request_id=request.request_id)
        required_modalities: set[ModalityType] = set()

        try:
            # 1. Privacy guardrails check
            self.security.enforce_privacy_guardrails(request.text)

            # 2. Modality Detection and Validation
            validated_attachments: list[Attachment] = []
            for att in request.attachments:
                # Content signature and format validation (do not trust client MIME alone)
                content = att.content_bytes or b""
                det_modality, canonical_mime = self.validator.validate(
                    filename=att.filename or "unknown",
                    content_bytes=content,
                    client_mime=att.mime_type,
                    declared_modality=att.type,
                )
                required_modalities.add(det_modality)

                # Normalized attachment with deterministic checksum (Spec 5, 10)
                norm_att = MediaNormalizer.create_attachment(
                    modality=det_modality,
                    mime_type=canonical_mime,
                    content_bytes=content,
                    filename=att.filename,
                    source=att.source,
                    duration=att.duration,
                )
                validated_attachments.append(norm_att)

            if request.screen_context:
                required_modalities.add(ModalityType.SCREEN)
            if request.audio_context:
                required_modalities.add(ModalityType.AUDIO)
            if request.text:
                required_modalities.add(ModalityType.TEXT)

            # Publish multimodal.requested event
            await self.events.emit_requested(
                request.request_id,
                request.user_id,
                [m.value for m in required_modalities],
                request.project_id,
            )

            # 3. Model Capability Resolution & Routing (Specs 28-31)
            selected_model = self.router.resolve_model_for_modalities(required_modalities)
            builder.model_id = selected_model.id

            # 4. Check safe cache for deduplication (Spec 69)
            cache_key = self._compute_cache_key(request.user_id, validated_attachments, request.text)
            if cache_key and cache_key in self._cache:
                cached = self._cache[cache_key]
                logger.info("Multimodal cache hit for user %s (key=%s)", request.user_id, cache_key[:12])
                return cached

            # 5. Processor Execution
            partial_results: list[MultimodalResult] = []
            uncertainty_notes: list[str] = []

            # Screen Context Inspection
            if request.screen_context:
                await self.events.emit_processing(request.request_id, request.user_id, "screen")
                screen_res = await self.screen_processor.inspect_screen(
                    screen_context=request.screen_context,
                    query=request.text or "Analyze current screen",
                    user_id=request.user_id,
                )
                partial_results.append(screen_res)
                await self.events.emit_screen_captured(
                    request.screen_context.device_id,
                    request.user_id,
                    request.screen_context.window_title,
                )

            # Live Audio Context Transcription
            if request.audio_context:
                await self.events.emit_processing(request.request_id, request.user_id, "audio")
                audio_res = await self.audio_processor.transcribe_and_analyze(
                    audio_context=request.audio_context,
                    user_prompt=request.text,
                    user_id=request.user_id,
                )
                partial_results.append(audio_res)

            # Attachment Processors
            for att in validated_attachments:
                await self.events.emit_processing(request.request_id, request.user_id, att.type.value)

                if att.type == ModalityType.IMAGE:
                    img_res = await self.image_processor.analyze_image(
                        attachment=att,
                        prompt=request.text or "Analyze image content",
                        user_id=request.user_id,
                        project_id=request.project_id,
                        model_id=selected_model.id,
                    )
                    partial_results.append(img_res)
                    await self.events.emit_image_processed(att.id, request.user_id, att.dimensions)

                elif att.type == ModalityType.AUDIO:
                    aud_res = await self.audio_processor.transcribe_and_analyze(
                        attachment=att,
                        user_prompt=request.text,
                        user_id=request.user_id,
                    )
                    partial_results.append(aud_res)
                    await self.events.emit_audio_transcribed(request.user_id, att.duration or 0.0, len(aud_res.evidence))

                elif att.type == ModalityType.VIDEO:
                    vid_res = await self.video_processor.process_video(
                        attachment=att,
                        user_prompt=request.text,
                        user_id=request.user_id,
                    )
                    partial_results.append(vid_res)
                    await self.events.emit_video_processed(att.id, request.user_id, len(vid_res.evidence))

                elif att.type == ModalityType.DOCUMENT:
                    doc_res = await self.document_processor.analyze_document(
                        attachment=att,
                        query=request.text or "Summarize document",
                        user_id=request.user_id,
                        project_id=request.project_id,
                    )
                    partial_results.append(doc_res)
                    await self.events.emit_document_processed(att.filename or "doc", request.user_id, len(doc_res.evidence))

            # 6. Synthesize Unified Result
            for pr in partial_results:
                builder.evidence.extend(pr.evidence)
                builder.sources.extend(pr.sources)
                builder.artifacts.extend(pr.artifacts)
                builder.modality_usage.update(pr.modality_usage)
                if pr.uncertainty_note:
                    uncertainty_notes.append(pr.uncertainty_note)

            # Combined summary
            if partial_results:
                combined_summary = "\n\n".join(pr.summary for pr in partial_results)
                builder.set_summary(combined_summary)
            else:
                builder.set_summary(f"Multimodal inquiry processed: '{request.text or ''}'.")

            if uncertainty_notes:
                builder.set_uncertainty("; ".join(uncertainty_notes))

            # 7. Token Usage Estimation (Spec 32)
            usage = self.router.calculate_usage(
                images=sum(1 for a in validated_attachments if a.type == ModalityType.IMAGE) + (1 if request.screen_context else 0),
                audio_seconds=sum(a.duration or 0.0 for a in validated_attachments if a.type == ModalityType.AUDIO) + (request.audio_context.duration_seconds if request.audio_context else 0.0),
                video_seconds=sum(a.duration or 0.0 for a in validated_attachments if a.type == ModalityType.VIDEO),
                video_frames=sum(len(p.evidence) for p in partial_results if any(e.source_type == ModalityType.VIDEO for e in p.evidence)),
                document_chunks=sum(len(p.evidence) for p in partial_results if any(e.source_type == ModalityType.DOCUMENT for e in p.evidence)),
                prompt_chars=len(request.text or ""),
            )
            builder.set_usage(
                estimated_tokens=usage.estimated_tokens,
                images=usage.image_count,
                audio_seconds=usage.audio_duration_seconds,
                video_frames=usage.video_frames,
            )

            result = builder.build()

            # Cache result if deduplicatable
            if cache_key:
                self._cache[cache_key] = result

            # Emit multimodal.completed
            await self.events.emit_completed(
                request.request_id,
                request.user_id,
                result.modality_usage,
                result.model,
            )
            return result

        except (MultimodalValidationError, MultimodalLimitExceededError) as exc:
            logger.warning("Multimodal validation or limit failure: %s", exc)
            err_code = getattr(exc, "error_code", MultimodalErrorState.INVALID_MEDIA)
            await self.events.emit_failed(request.request_id, request.user_id, err_code.value, str(exc))
            return builder.set_error(err_code, str(exc)).build()

        except MultimodalSecurityError as exc:
            logger.warning("Multimodal security policy failure: %s", exc)
            await self.events.emit_failed(request.request_id, request.user_id, exc.error_code.value, exc.message)
            return builder.set_error(exc.error_code, exc.message).build()

        except MultimodalRoutingError as exc:
            logger.warning("Multimodal model routing failure: %s", exc)
            await self.events.emit_failed(request.request_id, request.user_id, exc.error_code.value, exc.message)
            return builder.set_error(exc.error_code, exc.message).build()

        except Exception as exc:
            logger.exception("Unhandled multimodal processing failure: %s", exc)
            await self.events.emit_failed(request.request_id, request.user_id, MultimodalErrorState.PROCESSING_FAILED.value, str(exc))
            return builder.set_error(MultimodalErrorState.PROCESSING_FAILED, f"Internal multimodal processing failure: {exc}").build()

    def get_context_packet(self, request: MultimodalRequest, results: list[MultimodalResult]) -> MultimodalContextPacket:
        """Create structured context packet for Context Engine and agents."""
        return self.context_builder.build_packet(request, results)

    def _compute_cache_key(
        self,
        user_id: str,
        attachments: list[Attachment],
        query: str | None,
    ) -> str | None:
        """Generate user-scoped cache key from checksums and query (Spec 69, 70)."""
        if not attachments:
            return None
        checksums = "_".join(sorted(a.checksum for a in attachments))
        q_hash = MediaNormalizer.compute_sha256((query or "").encode("utf-8"))[:12]
        # Always user-scoped
        return f"{user_id}:{checksums}:{q_hash}"


# Global singleton instance
_multimodal_service: MultimodalService | None = None


def get_multimodal_service() -> MultimodalService:
    global _multimodal_service
    if _multimodal_service is None:
        _multimodal_service = MultimodalService()
    return _multimodal_service
