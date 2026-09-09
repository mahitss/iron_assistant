"""Pydantic schemas and canonical contracts for Kairo Multimodal Intelligence Layer."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ModalityType(str, Enum):
    """Primary modalities supported by Kairo."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    SCREEN = "screen"


class MultimodalStatus(str, Enum):
    """Lifecycle status of a multimodal request."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class MultimodalErrorState(str, Enum):
    """Authoritative multimodal error classifications (Spec 78)."""

    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    TOO_LARGE = "TOO_LARGE"
    TOO_LONG = "TOO_LONG"
    INVALID_MEDIA = "INVALID_MEDIA"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


class Attachment(BaseModel):
    """Metadata and references for an attached media or document artifact."""

    id: str = Field(default_factory=lambda: f"att_{uuid.uuid4().hex[:12]}")
    type: ModalityType
    source: str = Field(default="upload", description="upload, companion, local_file, buffer")
    mime_type: str
    size: int = Field(ge=0, description="Size in bytes")
    filename: str | None = None
    duration: float | None = Field(default=None, description="Duration in seconds if applicable")
    dimensions: tuple[int, int] | None = Field(default=None, description="(width, height) if applicable")
    checksum: str = Field(..., description="Stable SHA-256 hash for deduplication and traceability")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # Note: content_bytes is stored transiently for processing, excluded from dumped event payloads
    content_bytes: bytes | None = Field(default=None, exclude=True, repr=False)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ScreenContext(BaseModel):
    """Privileged screen capture metadata provided by Local Companion."""

    device_id: str
    authorized: bool = Field(default=False, description="Whether capture was authorized by user")
    active_state: str = Field(default="SCREEN_SHARING_ACTIVE", description="Visible UI capture state")
    resolution: tuple[int, int] | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    image_bytes: bytes | None = Field(default=None, exclude=True, repr=False)
    window_title: str | None = None
    application_name: str | None = None
    ephemeral: bool = Field(default=True, description="Must not be persisted permanently unless explicit")

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AudioContext(BaseModel):
    """Privileged audio capture metadata from Local Companion or explicit microphone toggle."""

    device_id: str | None = None
    microphone_authorized: bool = Field(default=False)
    sample_rate: int = 16000
    duration_seconds: float = 0.0
    active_state: str = Field(default="MICROPHONE_ACTIVE", description="Visible UI indicator state")
    ephemeral: bool = True


class MultimodalRequest(BaseModel):
    """Canonical request envelope for unified multimodal reasoning."""

    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    user_id: str
    project_id: str | None = None
    text: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    screen_context: ScreenContext | None = None
    audio_context: AudioContext | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MultimodalEvidenceItem(BaseModel):
    """Verifiable grounded citation or evidence extracted from media."""

    source_type: ModalityType
    identifier: str = Field(..., description="Filename, attachment_id, or device_id")
    page: int | None = None
    timestamp: str | None = Field(default=None, description="e.g. '00:31' or seconds")
    region: dict[str, Any] | None = Field(default=None, description="Bounding box or window coordinates")
    content: str = Field(..., description="Grounded excerpt, OCR content, or segment transcript")
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class MultimodalResult(BaseModel):
    """Structured response result returned by the Multimodal Intelligence Layer."""

    request_id: str
    status: MultimodalStatus = MultimodalStatus.COMPLETED
    summary: str
    evidence: list[MultimodalEvidenceItem] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    modality_usage: dict[str, Any] = Field(default_factory=dict)
    model: str = "kairo-multimodal-orchestrator"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    uncertainty_note: str | None = None
    error_code: MultimodalErrorState | None = None
    error_message: str | None = None


# --- API Request / Response DTOs ---

class AnalyzeMediaRequestDTO(BaseModel):
    """DTO for POST /api/v1/multimodal/analyze."""

    prompt: str = Field(..., min_length=1)
    project_id: str | None = None
    device_id: str | None = None
    capture_screen: bool = False
    attachments: list[dict[str, Any]] = Field(default_factory=list)


class TranscribeAudioRequestDTO(BaseModel):
    """DTO for POST /api/v1/multimodal/transcribe."""

    device_id: str | None = None
    audio_format: str = "wav"
    audio_base64: str | None = None
    duration_seconds: float | None = None


class ProcessMultimodalRequestDTO(BaseModel):
    """DTO for POST /api/v1/multimodal/process."""

    query: str | None = None
    project_id: str | None = None
    device_id: str | None = None
    media_type: ModalityType = ModalityType.IMAGE
    media_base64: str | None = None
    filename: str | None = None
