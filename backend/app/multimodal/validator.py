"""MIME validation, content signatures (magic numbers), and integrity checks (Specs 6, 9)."""

from __future__ import annotations

import os
from typing import Tuple

from app.multimodal.limits import MultimodalLimitExceededError, MultimodalLimits
from app.multimodal.schemas import ModalityType, MultimodalErrorState


class MultimodalValidationError(Exception):
    """Raised when media validation fails format, signature, or integrity checks."""

    def __init__(self, error_code: MultimodalErrorState, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class MediaValidator:
    """Rigorous validator inspecting file extensions, MIME types, and magic bytes."""

    # Supported format map: extension -> (canonical mime, ModalityType)
    SUPPORTED_EXTENSIONS: dict[str, tuple[str, ModalityType]] = {
        # Images
        ".png": ("image/png", ModalityType.IMAGE),
        ".jpg": ("image/jpeg", ModalityType.IMAGE),
        ".jpeg": ("image/jpeg", ModalityType.IMAGE),
        ".webp": ("image/webp", ModalityType.IMAGE),
        ".gif": ("image/gif", ModalityType.IMAGE),
        # Audio
        ".wav": ("audio/wav", ModalityType.AUDIO),
        ".mp3": ("audio/mpeg", ModalityType.AUDIO),
        ".ogg": ("audio/ogg", ModalityType.AUDIO),
        ".m4a": ("audio/mp4", ModalityType.AUDIO),
        # Video
        ".mp4": ("video/mp4", ModalityType.VIDEO),
        ".webm": ("video/webm", ModalityType.VIDEO),
        ".mov": ("video/quicktime", ModalityType.VIDEO),
        # Documents
        ".pdf": ("application/pdf", ModalityType.DOCUMENT),
        ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ModalityType.DOCUMENT),
        ".txt": ("text/plain", ModalityType.DOCUMENT),
        ".md": ("text/markdown", ModalityType.DOCUMENT),
        ".json": ("application/json", ModalityType.DOCUMENT),
        ".csv": ("text/csv", ModalityType.DOCUMENT),
    }

    def __init__(self, limits: MultimodalLimits | None = None) -> None:
        self.limits = limits or MultimodalLimits.load_from_settings()

    def validate(
        self,
        filename: str,
        content_bytes: bytes,
        client_mime: str | None = None,
        declared_modality: ModalityType | None = None,
    ) -> tuple[ModalityType, str]:
        """Verify content integrity, extension, size, and magic numbers.

        Returns verified (ModalityType, canonical_mime).
        """
        # 1. Zero-byte or empty check
        if not content_bytes or len(content_bytes) == 0:
            raise MultimodalValidationError(
                MultimodalErrorState.INVALID_MEDIA,
                "Uploaded media or document is empty (0 bytes).",
            )

        # 2. Extension check
        ext = os.path.splitext(filename.lower())[1] if filename else ""
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise MultimodalValidationError(
                MultimodalErrorState.UNSUPPORTED_FORMAT,
                f"Unsupported file format: '{ext or 'unknown'}'.",
            )

        canonical_mime, detected_modality = self.SUPPORTED_EXTENSIONS[ext]

        # Verify declared modality matches detected modality if specified
        if declared_modality and declared_modality != detected_modality:
            # Note: Screen captures are delivered as images
            if not (declared_modality == ModalityType.SCREEN and detected_modality == ModalityType.IMAGE):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    f"Declared modality '{declared_modality.value}' does not match file type '{detected_modality.value}'.",
                )

        # 3. Size limit check
        self.limits.validate_size(detected_modality, len(content_bytes))

        # 4. Content signature (magic number) verification - do not trust client MIME alone
        self._verify_content_signature(ext, content_bytes)

        return detected_modality, canonical_mime

    def _verify_content_signature(self, ext: str, content: bytes) -> None:
        """Inspect initial byte stream for canonical magic numbers."""
        header = content[:32]

        if ext == ".png":
            if not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted PNG image: missing canonical PNG signature header.",
                )
        elif ext in (".jpg", ".jpeg"):
            if not header.startswith(b"\xff\xd8\xff"):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted JPEG image: missing standard SOI marker.",
                )
        elif ext == ".gif":
            if not (header.startswith(b"GIF87a") or header.startswith(b"GIF89a")):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted GIF image: invalid GIF header signature.",
                )
        elif ext == ".webp":
            if not (header.startswith(b"RIFF") and b"WEBP" in header[8:16]):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted WebP image: missing RIFF/WEBP header.",
                )
        elif ext == ".pdf":
            if not header.startswith(b"%PDF-"):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted PDF document: missing standard '%PDF-' magic header.",
                )
        elif ext == ".wav":
            if not (header.startswith(b"RIFF") and b"WAVE" in header[8:16]):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted WAV audio: missing RIFF/WAVE header.",
                )
        elif ext in (".mp3", ".m4a"):
            # MP3 can start with ID3 tag or sync word 0xFFFB/0xFFF3/0xFFF2
            is_id3 = header.startswith(b"ID3")
            is_sync = len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
            is_ftyp = b"ftyp" in header[4:12]
            if not (is_id3 or is_sync or is_ftyp):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted audio file: unrecognized audio stream header.",
                )
        elif ext in (".mp4", ".mov"):
            if b"ftyp" not in header[4:12] and b"moov" not in header[4:12]:
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted MP4/QuickTime video: missing ftyp/moov box header.",
                )
        elif ext == ".docx":
            # DOCX is a ZIP container: starts with PK\x03\x04
            if not header.startswith(b"PK\x03\x04"):
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    "Corrupted DOCX document: invalid ZIP package header.",
                )
        elif ext in (".txt", ".md", ".json", ".csv"):
            # Text formats: verify UTF-8 decodeability without null bytes
            try:
                sample = content[:4096].decode("utf-8")
                if "\x00" in sample:
                    raise MultimodalValidationError(
                        MultimodalErrorState.INVALID_MEDIA,
                        f"Binary null bytes found in plaintext {ext} file.",
                    )
            except UnicodeDecodeError:
                raise MultimodalValidationError(
                    MultimodalErrorState.INVALID_MEDIA,
                    f"Plaintext file {ext} is not valid UTF-8 text.",
                )
