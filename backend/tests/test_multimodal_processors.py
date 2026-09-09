"""Tests for specialized multimodal processors across all modalities (Specs 8-27, 37-40, 77, 93, 94)."""

import pytest

from app.multimodal.normalizer import MediaNormalizer
from app.multimodal.processors.audio import AudioProcessor
from app.multimodal.processors.document import DocumentProcessor
from app.multimodal.processors.image import ImageProcessor
from app.multimodal.processors.screen import ScreenProcessor
from app.multimodal.processors.video import VideoProcessor
from app.multimodal.schemas import (
    AudioContext,
    ModalityType,
    MultimodalStatus,
    ScreenContext,
)


@pytest.mark.asyncio
async def test_image_processor_diagram_and_ocr():
    """Image analysis extracts OCR and grounded architectural description (Specs 8, 11, 37)."""
    processor = ImageProcessor()
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00"
    att = MediaNormalizer.create_attachment(
        modality=ModalityType.IMAGE,
        mime_type="image/png",
        content_bytes=png_bytes,
        filename="system_architecture_diagram.png",
    )

    result = await processor.analyze_image(
        attachment=att,
        prompt="Explain this architecture diagram",
        user_id="user_1",
    )
    assert result.status == MultimodalStatus.COMPLETED
    assert "architecture" in result.summary.lower()
    assert len(result.evidence) > 0
    assert result.evidence[0].source_type == ModalityType.IMAGE
    assert "BEGIN DERIVED_OCR_CONTENT" in result.evidence[0].content
    assert result.artifacts[0]["image_id"] == att.id


@pytest.mark.asyncio
async def test_image_processor_blurry_uncertainty():
    """Blurry or degraded images must declare uncertainty explicitly (Spec 63)."""
    processor = ImageProcessor()
    # Less than 100 bytes or named blurry
    att = MediaNormalizer.create_attachment(
        modality=ModalityType.IMAGE,
        mime_type="image/png",
        content_bytes=b"\x89PNG\r\n\x1a\n" + (b"\x00" * 20),
        filename="blurry_code.png",
    )
    result = await processor.analyze_image(
        attachment=att,
        prompt="What does the code say?",
        user_id="user_1",
    )
    assert result.uncertainty_note is not None
    assert "too blurry" in result.uncertainty_note.lower()


@pytest.mark.asyncio
async def test_audio_processor_transcription_and_action_items():
    """Audio processor produces timestamped segments and extracts action items (Specs 13, 15, 39)."""
    processor = AudioProcessor()
    att = MediaNormalizer.create_attachment(
        modality=ModalityType.AUDIO,
        mime_type="audio/wav",
        content_bytes=b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00",
        filename="meeting_actions.wav",
        duration=60.0,
    )

    result = await processor.transcribe_and_analyze(
        attachment=att,
        user_prompt="Extract the action items from this meeting",
        user_id="user_1",
    )
    assert result.status == MultimodalStatus.COMPLETED
    assert len(result.evidence) >= 2
    assert result.evidence[0].timestamp is not None
    assert "Action items" in result.summary or "Action Items:" in result.summary
    assert len(result.artifacts[0]["action_items"]) >= 1


@pytest.mark.asyncio
async def test_video_processor_bounded_sampling_and_partial_success():
    """Video processor enforces bounded sampling and handles partial failures (Specs 18, 77)."""
    processor = VideoProcessor()
    att = MediaNormalizer.create_attachment(
        modality=ModalityType.VIDEO,
        mime_type="video/mp4",
        content_bytes=b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom",
        filename="demo.mp4",
        duration=120.0,
    )

    # 1. Successful bounded run
    res_success = await processor.process_video(attachment=att, user_prompt="Summarize video")
    assert res_success.status == MultimodalStatus.COMPLETED
    assert res_success.artifacts[0]["sampled_frames"] <= 30
    assert len(res_success.artifacts[0]["key_moments"]) > 0

    # 2. Partial success run when audio fails
    res_partial = await processor.process_video(attachment=att, simulate_audio_failure=True)
    assert res_partial.status == MultimodalStatus.PARTIAL_SUCCESS
    assert "audio track was corrupted" in res_partial.uncertainty_note


@pytest.mark.asyncio
async def test_document_processor_page_citations_and_no_hallucination():
    """Document processor preserves page context and rejects hallucinating absent facts (Specs 22, 93, 94)."""
    processor = DocumentProcessor()
    doc_text = b"Kairo Architecture Overview\n\nSection 1: Microservice topology.\n\nSection 2: Database replication cluster."
    att = MediaNormalizer.create_attachment(
        modality=ModalityType.DOCUMENT,
        mime_type="application/pdf",
        content_bytes=doc_text,
        filename="architecture_spec.pdf",
    )

    # Grounded answer with citations
    res = await processor.analyze_document(
        attachment=att,
        query="Explain the architecture",
        user_id="user_1",
    )
    assert res.status == MultimodalStatus.COMPLETED
    assert any("Page 1" in s for s in res.sources)
    assert len(res.evidence) >= 1
    assert "BEGIN UNTRUSTED_DOCUMENT_CONTENT" in res.evidence[0].content

    # Hallucination test (Spec 94): Query about absent Fact B
    res_absent = await processor.analyze_document(
        attachment=att,
        query="What does it say about Fact B?",
        user_id="user_1",
    )
    assert "not present in the provided document" in res_absent.summary.lower()


@pytest.mark.asyncio
async def test_screen_processor_inspects_and_decouples_computer_action():
    """Screen inspection observes UI state but never triggers computer control action (Specs 26, 27)."""
    processor = ScreenProcessor()
    screen_ctx = ScreenContext(
        device_id="desktop-test-1",
        authorized=True,
        active_state="SCREEN_SHARING_ACTIVE",
        window_title="Deployment Console - Failed Pod",
        application_name="Kubernetes Dashboard",
    )

    result = await processor.inspect_screen(
        screen_context=screen_ctx,
        query="What is wrong on my screen?",
        user_id="user_1",
    )
    assert result.status == MultimodalStatus.COMPLETED
    assert "failed deployment" in result.summary.lower()
    assert result.artifacts[0]["computer_action_triggered"] is False
    assert result.artifacts[0]["ephemeral"] is True
