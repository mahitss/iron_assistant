"""Tests for Multimodal Model Routing, capability matching, and Context Packet Assembly (Specs 28-35, 96)."""

import pytest

from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry, create_default_registry
from app.multimodal.context import MultimodalContextBuilder
from app.multimodal.limits import MultimodalLimits
from app.multimodal.normalizer import MediaNormalizer
from app.multimodal.router import MultimodalModelRouter, MultimodalRoutingError
from app.multimodal.schemas import (
    ModalityType,
    MultimodalErrorState,
    MultimodalEvidenceItem,
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
)


def test_router_selects_multimodal_gemini():
    """Request with IMAGE + TEXT routes to multimodal capable model (Specs 28, 30, 31)."""
    registry = create_default_registry()
    router = MultimodalModelRouter(registry)

    model = router.resolve_model_for_modalities({ModalityType.IMAGE, ModalityType.TEXT})
    assert model.id == "google/gemini-2.0-flash-001"
    assert ModelCapability.VISION in model.capabilities or ModelCapability.IMAGE in model.capabilities


def test_router_raises_capability_unavailable_when_missing():
    """If no compatible model exists, return CAPABILITY_UNAVAILABLE (Spec 29)."""
    # Create empty registry with only text model
    registry = ModelRegistry()
    registry.register_model(
        ModelDefinition(
            id="text-only-model",
            provider="test",
            capabilities={ModelCapability.GENERAL},
            enabled=True,
        )
    )
    router = MultimodalModelRouter(registry)

    with pytest.raises(MultimodalRoutingError) as exc:
        router.resolve_model_for_modalities({ModalityType.IMAGE})
    assert exc.value.error_code == MultimodalErrorState.CAPABILITY_UNAVAILABLE
    assert "No enabled model found" in exc.value.message


def test_router_usage_and_token_estimation():
    """Track image count, audio duration, video frames, and tokens (Spec 32)."""
    router = MultimodalModelRouter(create_default_registry())
    usage = router.calculate_usage(
        images=2,
        audio_seconds=120.0,
        video_seconds=60.0,
        video_frames=12,
        document_chunks=4,
        prompt_chars=400,
    )
    assert usage.image_count == 2
    assert usage.audio_duration_seconds == 120.0
    assert usage.video_frames == 12
    assert usage.document_chunk_count == 4
    assert usage.estimated_tokens > 0


def test_cross_modal_context_packet_assembly():
    """Cross-modal context: text + screen + document (Spec 96)."""
    builder = MultimodalContextBuilder()
    req = MultimodalRequest(
        user_id="user_1",
        text="Compare the screenshot with the architecture document.",
    )

    doc_res = MultimodalResult(
        request_id="res_doc",
        status=MultimodalStatus.COMPLETED,
        summary="Architecture summary",
        evidence=[
            MultimodalEvidenceItem(
                source_type=ModalityType.DOCUMENT,
                identifier="spec.pdf",
                page=3,
                content="Grounded document text: Microservices use PostgreSQL.",
            )
        ],
        model="gemini",
    )

    screen_res = MultimodalResult(
        request_id="res_scr",
        status=MultimodalStatus.COMPLETED,
        summary="Screen observation",
        evidence=[
            MultimodalEvidenceItem(
                source_type=ModalityType.SCREEN,
                identifier="desktop_1",
                content="Active window: DB Connection Error dialog on port 5432.",
            )
        ],
        model="gemini",
    )

    packet = builder.build_packet(req, [doc_res, screen_res])
    prompt_block = packet.to_system_prompt_block()

    assert "User Inquiry:" in prompt_block
    assert "Compare the screenshot with the architecture document." in prompt_block
    assert "Authorized Screen Context Observation:" in prompt_block
    assert "Grounded Document Evidence:" in prompt_block
    assert "spec.pdf (Page 3)" in prompt_block
    assert "DB Connection Error dialog" in prompt_block
