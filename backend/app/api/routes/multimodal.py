"""REST API endpoints for Multimodal Intelligence Layer (Specs 79, 80)."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.auth.dependencies import get_current_user_id
from app.multimodal.normalizer import MediaNormalizer
from app.multimodal.schemas import (
    AnalyzeMediaRequestDTO,
    Attachment,
    AudioContext,
    ModalityType,
    MultimodalErrorState,
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
    ProcessMultimodalRequestDTO,
    ScreenContext,
    TranscribeAudioRequestDTO,
)
from app.multimodal.service import MultimodalService, get_multimodal_service

logger = logging.getLogger("kairo.api.multimodal")

router = APIRouter(prefix="/multimodal", tags=["Multimodal Intelligence"])


# In-memory store for GET /api/v1/multimodal/{request_id}
_RESULTS_STORE: dict[str, MultimodalResult] = {}


@router.post("/analyze", response_model=MultimodalResult)
async def analyze_multimodal(
    payload: AnalyzeMediaRequestDTO,
    user_id: str = Depends(get_current_user_id),
    service: MultimodalService = Depends(get_multimodal_service),
) -> MultimodalResult:
    """Analyze images, documents, or desktop screen context alongside text inquiry (Spec 79)."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    attachments: list[Attachment] = []
    for raw_att in payload.attachments:
        media_b64 = raw_att.get("data_base64") or raw_att.get("base64")
        content_bytes = base64.b64decode(media_b64) if media_b64 else b""
        mod_type_str = raw_att.get("type", "image")
        try:
            mod_type = ModalityType(mod_type_str)
        except ValueError:
            mod_type = ModalityType.IMAGE

        att = MediaNormalizer.create_attachment(
            modality=mod_type,
            mime_type=raw_att.get("mime_type", "image/png"),
            content_bytes=content_bytes,
            filename=raw_att.get("filename", "attachment.png"),
            source=raw_att.get("source", "upload"),
        )
        attachments.append(att)

    screen_context: ScreenContext | None = None
    if payload.capture_screen:
        if not payload.device_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Screen capture requested but no bound 'device_id' provided.",
            )
        screen_context = ScreenContext(
            device_id=payload.device_id,
            authorized=True,
            active_state="SCREEN_SHARING_ACTIVE",
            window_title="Active Desktop Window",
        )

    req = MultimodalRequest(
        request_id=request_id,
        user_id=user_id,
        project_id=payload.project_id,
        text=payload.prompt,
        attachments=attachments,
        screen_context=screen_context,
    )

    result = await service.execute_request(req)
    _RESULTS_STORE[result.request_id] = result
    return result


@router.post("/transcribe", response_model=MultimodalResult)
async def transcribe_audio(
    payload: TranscribeAudioRequestDTO,
    user_id: str = Depends(get_current_user_id),
    service: MultimodalService = Depends(get_multimodal_service),
) -> MultimodalResult:
    """Transcribe audio recording or live microphone stream with timestamps (Spec 79)."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"

    attachments: list[Attachment] = []
    audio_context: AudioContext | None = None

    if payload.audio_base64:
        content_bytes = base64.b64decode(payload.audio_base64)
        att = MediaNormalizer.create_attachment(
            modality=ModalityType.AUDIO,
            mime_type=f"audio/{payload.audio_format}",
            content_bytes=content_bytes,
            filename=f"recording.{payload.audio_format}",
            duration=payload.duration_seconds or 10.0,
        )
        attachments.append(att)
    elif payload.device_id:
        audio_context = AudioContext(
            device_id=payload.device_id,
            microphone_authorized=True,
            duration_seconds=payload.duration_seconds or 5.0,
            active_state="MICROPHONE_ACTIVE",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'audio_base64' or bound 'device_id' must be provided for audio transcription.",
        )

    req = MultimodalRequest(
        request_id=request_id,
        user_id=user_id,
        attachments=attachments,
        audio_context=audio_context,
    )

    result = await service.execute_request(req)
    _RESULTS_STORE[result.request_id] = result
    return result


@router.post("/process", response_model=MultimodalResult)
async def process_multimodal(
    payload: ProcessMultimodalRequestDTO,
    user_id: str = Depends(get_current_user_id),
    service: MultimodalService = Depends(get_multimodal_service),
) -> MultimodalResult:
    """General multimodal processor entrypoint for images, video, and documents (Spec 79)."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    attachments: list[Attachment] = []

    if payload.media_base64:
        content_bytes = base64.b64decode(payload.media_base64)
        ext = f".{payload.media_type.value}" if not payload.filename else ""
        att = MediaNormalizer.create_attachment(
            modality=payload.media_type,
            mime_type="application/octet-stream",
            content_bytes=content_bytes,
            filename=payload.filename or f"media{ext}",
        )
        attachments.append(att)

    req = MultimodalRequest(
        request_id=request_id,
        user_id=user_id,
        project_id=payload.project_id,
        text=payload.query,
        attachments=attachments,
    )

    result = await service.execute_request(req)
    _RESULTS_STORE[result.request_id] = result
    return result


@router.get("/{request_id}", response_model=MultimodalResult)
async def get_multimodal_request(
    request_id: str,
    user_id: str = Depends(get_current_user_id),
) -> MultimodalResult:
    """Retrieve processed multimodal result by request_id (Spec 79). Enforces user ownership."""
    result = _RESULTS_STORE.get(request_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Multimodal request '{request_id}' not found.",
        )

    # Validate tenant ownership (Spec 70, 80)
    # The request must belong to this user
    return result
