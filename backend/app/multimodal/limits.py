"""Centralized resource bounds, limits, and budget enforcement for Multimodal Intelligence (Spec 7, 19, 32, 35)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from app.config.settings import get_settings
from app.multimodal.schemas import ModalityType, MultimodalErrorState


class MultimodalLimitExceededError(Exception):
    """Raised when a media file or context payload exceeds configured boundaries."""

    def __init__(self, error_code: MultimodalErrorState, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass(frozen=True)
class MultimodalLimits:
    """Configured thresholds and quotas for all supported modalities."""

    max_image_size_bytes: int
    max_audio_size_bytes: int
    max_video_size_bytes: int
    max_document_size_bytes: int
    max_audio_duration_seconds: float
    max_video_duration_seconds: float
    max_video_frames: int
    video_sample_interval_seconds: int
    max_image_dimension: int
    max_images_per_request: int
    max_document_chunks: int
    max_context_tokens: int

    @classmethod
    def load_from_settings(cls) -> MultimodalLimits:
        """Instantiate limits from centralized application settings."""
        settings = get_settings()
        return cls(
            max_image_size_bytes=getattr(settings, "KAIRO_MAX_IMAGE_SIZE_BYTES", 15728640),
            max_audio_size_bytes=getattr(settings, "KAIRO_MAX_AUDIO_SIZE_BYTES", 26214400),
            max_video_size_bytes=getattr(settings, "KAIRO_MAX_VIDEO_SIZE_BYTES", 52428800),
            max_document_size_bytes=getattr(settings, "KAIRO_MAX_DOCUMENT_SIZE_BYTES", 20971520),
            max_audio_duration_seconds=float(getattr(settings, "KAIRO_MAX_AUDIO_DURATION_SECONDS", 300.0)),
            max_video_duration_seconds=float(getattr(settings, "KAIRO_MAX_VIDEO_DURATION_SECONDS", 180.0)),
            max_video_frames=getattr(settings, "KAIRO_MAX_VIDEO_FRAMES", 30),
            video_sample_interval_seconds=getattr(settings, "KAIRO_VIDEO_SAMPLE_INTERVAL_SECONDS", 5),
            max_image_dimension=getattr(settings, "KAIRO_MAX_IMAGE_DIMENSION", 4096),
            max_images_per_request=getattr(settings, "KAIRO_MAX_MULTIMODAL_IMAGES", 5),
            max_document_chunks=getattr(settings, "KAIRO_MAX_MULTIMODAL_DOCUMENT_CHUNKS", 10),
            max_context_tokens=getattr(settings, "KAIRO_MAX_MULTIMODAL_CONTEXT_TOKENS", 8000),
        )

    def validate_size(self, modality: ModalityType, size_bytes: int) -> None:
        """Validate raw artifact size against modality limit."""
        if modality == ModalityType.IMAGE and size_bytes > self.max_image_size_bytes:
            raise MultimodalLimitExceededError(
                MultimodalErrorState.TOO_LARGE,
                f"Image size {size_bytes} bytes exceeds maximum limit of {self.max_image_size_bytes} bytes.",
            )
        elif modality == ModalityType.AUDIO and size_bytes > self.max_audio_size_bytes:
            raise MultimodalLimitExceededError(
                MultimodalErrorState.TOO_LARGE,
                f"Audio size {size_bytes} bytes exceeds maximum limit of {self.max_audio_size_bytes} bytes.",
            )
        elif modality == ModalityType.VIDEO and size_bytes > self.max_video_size_bytes:
            raise MultimodalLimitExceededError(
                MultimodalErrorState.TOO_LARGE,
                f"Video size {size_bytes} bytes exceeds maximum limit of {self.max_video_size_bytes} bytes.",
            )
        elif modality == ModalityType.DOCUMENT and size_bytes > self.max_document_size_bytes:
            raise MultimodalLimitExceededError(
                MultimodalErrorState.TOO_LARGE,
                f"Document size {size_bytes} bytes exceeds maximum limit of {self.max_document_size_bytes} bytes.",
            )

    def validate_duration(self, modality: ModalityType, duration_seconds: float) -> None:
        """Validate playback or recording duration against limits."""
        if modality == ModalityType.AUDIO and duration_seconds > self.max_audio_duration_seconds:
            raise MultimodalLimitExceededError(
                MultimodalErrorState.TOO_LONG,
                f"Audio duration {duration_seconds:.1f}s exceeds limit of {self.max_audio_duration_seconds:.1f}s.",
            )
        elif modality == ModalityType.VIDEO and duration_seconds > self.max_video_duration_seconds:
            raise MultimodalLimitExceededError(
                MultimodalErrorState.TOO_LONG,
                f"Video duration {duration_seconds:.1f}s exceeds limit of {self.max_video_duration_seconds:.1f}s.",
            )

    def validate_image_dimensions(self, dimensions: Tuple[int, int]) -> None:
        """Ensure image dimensions do not exceed maximum resolution."""
        width, height = dimensions
        if width > self.max_image_dimension or height > self.max_image_dimension:
            raise MultimodalLimitExceededError(
                MultimodalErrorState.TOO_LARGE,
                f"Image dimensions {width}x{height} exceed maximum allowed resolution of {self.max_image_dimension}px.",
            )

    def get_bounded_frame_count(self, duration_seconds: float) -> int:
        """Calculate bounded number of frames to sample for a video."""
        if duration_seconds <= 0:
            return 1
        raw_frames = int(duration_seconds // max(1, self.video_sample_interval_seconds)) + 1
        return min(raw_frames, self.max_video_frames)
