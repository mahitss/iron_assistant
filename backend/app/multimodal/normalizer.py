"""Artifact normalization, stable checksum computation, and safe metadata extraction (Specs 5, 10)."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import io
import struct
from typing import Tuple

from app.multimodal.schemas import Attachment, ModalityType


class MediaNormalizer:
    """Computes stable cryptographic digests and extracts non-destructive metadata."""

    @staticmethod
    def compute_sha256(content: bytes) -> str:
        """Calculate deterministic SHA-256 checksum for deduplication and cache safety."""
        hasher = hashlib.sha256()
        hasher.update(content)
        return hasher.hexdigest()

    @classmethod
    def create_attachment(
        cls,
        modality: ModalityType,
        mime_type: str,
        content_bytes: bytes,
        filename: str | None = None,
        source: str = "upload",
        duration: float | None = None,
    ) -> Attachment:
        """Produce a normalized Attachment object without mutating or lossily recompressing original bytes."""
        checksum = cls.compute_sha256(content_bytes)
        size = len(content_bytes)

        dimensions: tuple[int, int] | None = None
        if modality in (ModalityType.IMAGE, ModalityType.SCREEN):
            dimensions = cls.extract_image_dimensions(content_bytes)

        return Attachment(
            type=modality,
            source=source,
            mime_type=mime_type,
            size=size,
            filename=filename,
            duration=duration,
            dimensions=dimensions,
            checksum=checksum,
            content_bytes=content_bytes,
            created_at=datetime.now(UTC),
        )

    @staticmethod
    def extract_image_dimensions(content: bytes) -> tuple[int, int] | None:
        """Safely parse image width and height without full decompression where possible."""
        try:
            # PNG width & height are 4-byte integers at offset 16 and 20
            if content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 24:
                w, h = struct.unpack(">II", content[16:24])
                return (w, h)

            # GIF dimensions at offset 6 (2 bytes width, 2 bytes height, little-endian)
            if (content.startswith(b"GIF87a") or content.startswith(b"GIF89a")) and len(content) >= 10:
                w, h = struct.unpack("<HH", content[6:10])
                return (w, h)

            # Fallback to PIL if installed and available
            try:
                from PIL import Image

                with Image.open(io.BytesIO(content)) as img:
                    return img.size
            except Exception:
                pass

        except Exception:
            pass

        return None
