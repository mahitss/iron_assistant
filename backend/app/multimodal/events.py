"""Event Bus integration and safe audit telemetry without raw media payloads (Specs 66, 67, 68)."""

from __future__ import annotations

import logging
from typing import Any

from app.events.bus import get_event_bus
from app.events.schemas import Event, EventSource, ReplaySafety
from app.security.audit import AuditLogger

logger = logging.getLogger("kairo.multimodal.events")


class MultimodalEventPublisher:
    """Publishes sanitized multimodal lifecycle events to the central EventBus."""

    def __init__(self) -> None:
        self.bus = get_event_bus()

    async def emit_requested(
        self,
        request_id: str,
        user_id: str,
        modalities: list[str],
        project_id: str | None = None,
    ) -> None:
        """Publish multimodal.requested event."""
        await self._publish_event(
            event_type="multimodal.requested",
            user_id=user_id,
            details={
                "request_id": request_id,
                "modalities": modalities,
                "project_id": project_id,
            },
        )

    async def emit_processing(
        self,
        request_id: str,
        user_id: str,
        current_modality: str,
    ) -> None:
        """Publish multimodal.processing event."""
        await self._publish_event(
            event_type="multimodal.processing",
            user_id=user_id,
            details={
                "request_id": request_id,
                "current_modality": current_modality,
            },
        )

    async def emit_completed(
        self,
        request_id: str,
        user_id: str,
        modality_usage: dict[str, Any],
        model: str,
    ) -> None:
        """Publish multimodal.completed event (never includes raw image/audio bytes)."""
        await self._publish_event(
            event_type="multimodal.completed",
            user_id=user_id,
            details={
                "request_id": request_id,
                "modality_usage": modality_usage,
                "model": model,
            },
        )

    async def emit_failed(
        self,
        request_id: str,
        user_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        """Publish multimodal.failed event."""
        await self._publish_event(
            event_type="multimodal.failed",
            user_id=user_id,
            details={
                "request_id": request_id,
                "error_code": error_code,
                "error_message": error_message,
            },
        )

    async def emit_image_processed(self, attachment_id: str, user_id: str, dimensions: tuple[int, int] | None) -> None:
        await self._publish_event("image.processed", user_id, {"attachment_id": attachment_id, "dimensions": dimensions})

    async def emit_audio_transcribed(self, user_id: str, duration_seconds: float, segment_count: int) -> None:
        await self._publish_event("audio.transcribed", user_id, {"duration_seconds": duration_seconds, "segments": segment_count})

    async def emit_video_processed(self, attachment_id: str, user_id: str, sampled_frames: int) -> None:
        await self._publish_event("video.processed", user_id, {"attachment_id": attachment_id, "sampled_frames": sampled_frames})

    async def emit_document_processed(self, filename: str, user_id: str, chunk_count: int) -> None:
        await self._publish_event("document.processed", user_id, {"filename": filename, "chunks": chunk_count})

    async def emit_screen_captured(self, device_id: str, user_id: str, window_title: str | None) -> None:
        """Audit log and publish screen.captured without storing raw screen pixels."""
        try:
            await AuditLogger.log_event(
                db_session=None,
                user_id=user_id,
                event_type="SCREEN_CAPTURE_OBSERVED",
                metadata={"device_id": device_id, "window_title": window_title},
            )
        except Exception as exc:
            logger.debug("Audit logger record skipped: %s", exc)
        await self._publish_event("screen.captured", user_id, {"device_id": device_id, "window_title": window_title})

    async def _publish_event(self, event_type: str, user_id: str, details: dict[str, Any]) -> None:
        """Safely dispatch event into bus."""
        try:
            event = Event(
                event_type=event_type,
                source=EventSource.MULTIMODAL if hasattr(EventSource, "MULTIMODAL") else EventSource.SYSTEM,
                user_id=user_id,
                payload=details,
            )
            await self.bus.publish(event)
        except Exception as exc:
            logger.warning("Failed to dispatch multimodal event %s: %s", event_type, exc)
