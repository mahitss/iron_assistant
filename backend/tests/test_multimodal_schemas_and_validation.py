"""Tests for Multimodal schemas, limits, checksums, and content signature validation (Specs 4-7, 9-10)."""

import pytest

from app.multimodal.limits import MultimodalLimitExceededError, MultimodalLimits
from app.multimodal.normalizer import MediaNormalizer
from app.multimodal.schemas import (
    Attachment,
    ModalityType,
    MultimodalErrorState,
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
)
from app.multimodal.validator import MediaValidator, MultimodalValidationError


def test_multimodal_schema_instantiation():
    """Verify clean instantiation and defaults for canonical schemas."""
    att = MediaNormalizer.create_attachment(
        modality=ModalityType.IMAGE,
        mime_type="image/png",
        content_bytes=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00",
        filename="diagram.png",
    )
    assert att.id.startswith("att_")
    assert att.type == ModalityType.IMAGE
    assert att.checksum is not None
    assert len(att.checksum) == 64  # SHA-256 hex digest length

    req = MultimodalRequest(
        user_id="user_123",
        text="Explain this diagram",
        attachments=[att],
    )
    assert req.request_id.startswith("req_")
    assert req.user_id == "user_123"
    assert len(req.attachments) == 1


def test_validator_magic_bytes_png():
    """Validate genuine PNG magic header verification."""
    validator = MediaValidator()
    valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x20\x00\x00\x00\x20"
    modality, mime = validator.validate("screenshot.png", valid_png)
    assert modality == ModalityType.IMAGE
    assert mime == "image/png"


def test_validator_magic_bytes_jpeg():
    """Validate genuine JPEG SOI marker verification."""
    validator = MediaValidator()
    valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    modality, mime = validator.validate("photo.jpg", valid_jpeg)
    assert modality == ModalityType.IMAGE
    assert mime == "image/jpeg"


def test_validator_magic_bytes_pdf():
    """Validate genuine PDF magic header verification."""
    validator = MediaValidator()
    valid_pdf = b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    modality, mime = validator.validate("architecture.pdf", valid_pdf)
    assert modality == ModalityType.DOCUMENT
    assert mime == "application/pdf"


def test_validator_magic_bytes_wav():
    """Validate genuine WAV magic header verification."""
    validator = MediaValidator()
    valid_wav = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
    modality, mime = validator.validate("speech.wav", valid_wav)
    assert modality == ModalityType.AUDIO
    assert mime == "audio/wav"


def test_validator_rejects_corrupted_png():
    """Reject corrupted PNG files with non-PNG headers (Spec 9)."""
    validator = MediaValidator()
    corrupted = b"NOT_A_PNG_FILE_HEADER_GARBAGE"
    with pytest.raises(MultimodalValidationError) as exc:
        validator.validate("malicious.png", corrupted)
    assert exc.value.error_code == MultimodalErrorState.INVALID_MEDIA
    assert "Corrupted PNG image" in str(exc.value)


def test_validator_rejects_empty_file():
    """Reject 0-byte media artifacts."""
    validator = MediaValidator()
    with pytest.raises(MultimodalValidationError) as exc:
        validator.validate("empty.png", b"")
    assert exc.value.error_code == MultimodalErrorState.INVALID_MEDIA


def test_validator_rejects_unsupported_format():
    """Reject unsupported file extensions."""
    validator = MediaValidator()
    with pytest.raises(MultimodalValidationError) as exc:
        validator.validate("archive.exe", b"MZ\x90\x00")
    assert exc.value.error_code == MultimodalErrorState.UNSUPPORTED_FORMAT


def test_limits_oversized_image():
    """Enforce centralized image size boundaries (Spec 7)."""
    limits = MultimodalLimits(
        max_image_size_bytes=1000,
        max_audio_size_bytes=1000,
        max_video_size_bytes=1000,
        max_document_size_bytes=1000,
        max_audio_duration_seconds=300.0,
        max_video_duration_seconds=180.0,
        max_video_frames=30,
        video_sample_interval_seconds=5,
        max_image_dimension=4096,
        max_images_per_request=5,
        max_document_chunks=10,
        max_context_tokens=8000,
    )
    validator = MediaValidator(limits=limits)
    large_png = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 2000)
    with pytest.raises(MultimodalLimitExceededError) as exc:
        validator.validate("big.png", large_png)
    assert exc.value.error_code == MultimodalErrorState.TOO_LARGE


def test_stable_checksum_deduplication():
    """Verify SHA-256 stable hashing produces deterministic identical checksums."""
    sample_bytes = b"Deterministic multimodal payload 12345"
    hash1 = MediaNormalizer.compute_sha256(sample_bytes)
    hash2 = MediaNormalizer.compute_sha256(sample_bytes)
    assert hash1 == hash2
    assert len(hash1) == 64
