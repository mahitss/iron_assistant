"""Multimodal processor handling OCR, visual descriptions, and audio/video transcripts with timestamps."""

import hashlib
import logging
import re
from typing import Any

from app.knowledge.schemas import (
    ChunkContentType,
    ChunkMetadata,
    DocumentChunk,
    FreshnessState,
    RAGSourceType,
    TrustTier,
)

logger = logging.getLogger("kairo.knowledge.multimodal")


class MultimodalRetriever:
    """Processes multimodal assets into structured chunks with positional, visual, or temporal metadata."""

    def process_transcript(
        self,
        transcript_data: list[dict[str, Any]] | str,
        media_id: str,
        title: str = "Media Recording",
        source_url: str | None = None,
        user_id: str = "default_user",
        project_id: str | None = None,
        source_type: RAGSourceType = RAGSourceType.AUDIO_TRANSCRIPT,
    ) -> list[DocumentChunk]:
        """Convert timestamped transcript turns into temporal chunks."""
        chunks: list[DocumentChunk] = []

        segments: list[dict[str, Any]] = []
        if isinstance(transcript_data, str):
            # Parse text with format [HH:MM:SS] Speaker: Text or (00:15) Text
            segments = self._parse_text_transcript(transcript_data)
        else:
            segments = transcript_data

        if not segments:
            return chunks

        # Group turns into ~30-60s or 5-turn temporal windows
        window_size = 5
        for i in range(0, len(segments), window_size):
            group = segments[i : i + window_size]
            start_time = float(group[0].get("start", 0.0))
            end_time = float(group[-1].get("end", start_time + 10.0))

            speakers = {s.get("speaker", "Speaker") for s in group if s.get("speaker")}
            speaker_label = ", ".join(speakers) if speakers else "Unknown"

            content_lines = []
            for item in group:
                spk = item.get("speaker", "")
                txt = item.get("text", "").strip()
                t_str = self._format_timestamp(float(item.get("start", 0.0)))
                if spk:
                    content_lines.append(f"[{t_str}] {spk}: {txt}")
                else:
                    content_lines.append(f"[{t_str}] {txt}")

            body = "\n".join(content_lines)
            chunk_id = f"{media_id}_trans_{i // window_size}"
            content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

            t_start_fmt = self._format_timestamp(start_time)
            t_end_fmt = self._format_timestamp(end_time)
            section_label = f"Time {t_start_fmt} - {t_end_fmt}"

            meta = ChunkMetadata(
                chunk_id=chunk_id,
                document_id=media_id,
                section=section_label,
                section_id=f"time_{int(start_time)}_{int(end_time)}",
                headings=[title, section_label],
                content_type=ChunkContentType.TRANSCRIPT_SEGMENT,
                start_time=start_time,
                end_time=end_time,
                speaker=speaker_label,
                source_url=source_url,
                user_id=user_id,
                project_id=project_id,
                freshness=FreshnessState.FRESH,
                source_type=source_type,
                trust_tier=TrustTier.USER_UPLOAD,
            )

            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    content=body,
                    metadata=meta,
                    content_hash=content_hash,
                )
            )

        return chunks

    def process_image_ocr(
        self,
        image_id: str,
        ocr_text: str,
        image_caption: str | None = None,
        source_url: str | None = None,
        user_id: str = "default_user",
        project_id: str | None = None,
    ) -> list[DocumentChunk]:
        """Convert image OCR and captioning into searchable knowledge chunks."""
        chunks: list[DocumentChunk] = []
        body_parts = []
        if image_caption:
            body_parts.append(f"Visual Caption: {image_caption}")
        if ocr_text:
            body_parts.append(f"Extracted Text:\n{ocr_text.strip()}")

        content = "\n\n".join(body_parts).strip()
        if not content:
            return chunks

        chunk_id = f"{image_id}_ocr_0"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        meta = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=image_id,
            section="Visual Content",
            section_id="img_ocr_sec",
            headings=["Image OCR & Caption"],
            content_type=ChunkContentType.IMAGE_CAPTION,
            source_url=source_url,
            user_id=user_id,
            project_id=project_id,
            freshness=FreshnessState.FRESH,
            source_type=RAGSourceType.IMAGE_OCR,
            trust_tier=TrustTier.USER_UPLOAD,
        )

        chunks.append(
            DocumentChunk(
                id=chunk_id,
                content=content,
                metadata=meta,
                content_hash=content_hash,
            )
        )

        return chunks

    def _parse_text_transcript(self, text: str) -> list[dict[str, Any]]:
        """Parse lines like '[01:23] Alice: Hello world' or '(00:15) Some words'."""
        lines = text.splitlines()
        segments = []
        time_re = re.compile(r"[\[\(](\d{1,2}:\d{2}(?::\d{2})?)[\]\)]\s*(?:([a-zA-Z0-9_\s]+):)?\s*(.+)")

        default_start = 0.0
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            m = time_re.match(line_str)
            if m:
                t_str, spk, content = m.group(1), m.group(2), m.group(3)
                seconds = self._parse_seconds(t_str)
                segments.append({
                    "start": seconds,
                    "end": seconds + 5.0,
                    "speaker": spk.strip() if spk else None,
                    "text": content.strip(),
                })
            else:
                segments.append({
                    "start": default_start,
                    "end": default_start + 5.0,
                    "speaker": None,
                    "text": line_str,
                })
                default_start += 5.0

        return segments

    def _parse_seconds(self, t_str: str) -> float:
        parts = [float(p) for p in t_str.split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return 0.0

    def _format_timestamp(self, seconds: float) -> str:
        s = int(seconds)
        hrs = s // 3600
        mins = (s % 3600) // 60
        secs = s % 60
        if hrs > 0:
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"
