"""Smart content-aware chunker respecting AST boundaries, headings, tables, and transcripts."""

import hashlib
import logging
from typing import Any

from app.knowledge.parsing.parser import ParsedBlock, ParsedDocument
from app.knowledge.schemas import (
    TRUST_WEIGHTS,
    ChunkContentType,
    ChunkMetadata,
    DocumentChunk,
    FreshnessState,
    RAGSourceType,
    TrustTier,
)

logger = logging.getLogger("kairo.knowledge.chunking")


class SmartChunker:
    """Intelligently chunks parsed documents according to their content type without fragmenting semantic units."""

    def __init__(
        self,
        target_chunk_chars: int = 1800,
        max_chunk_chars: int = 3600,
        min_chunk_chars: int = 150,
    ) -> None:
        self.target_chunk_chars = target_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars

    def chunk_document(
        self,
        parsed_doc: ParsedDocument,
        user_id: str = "default_user",
        project_id: str | None = None,
        source_url: str | None = None,
        commit_hash: str | None = None,
        file_path: str | None = None,
        freshness: FreshnessState = FreshnessState.FRESH,
        trust_tier: TrustTier = TrustTier.USER_UPLOAD,
    ) -> list[DocumentChunk]:
        """Convert a ParsedDocument into an ordered list of DocumentChunks."""
        chunks: list[DocumentChunk] = []
        blocks = parsed_doc.blocks

        if not blocks:
            return chunks

        i = 0
        chunk_idx = 0

        while i < len(blocks):
            block = blocks[i]

            # 1. Code Blocks & Functions: NEVER split across chunks unless single block exceeds max_chunk_chars
            if block.content_type == ChunkContentType.CODE_BLOCK:
                code_chunks = self._chunk_code_block(block)
                for c_content, s_line, e_line in code_chunks:
                    chunks.append(
                        self._build_chunk(
                            chunk_id=f"{parsed_doc.document_id}_chk_{chunk_idx}",
                            document_id=parsed_doc.document_id,
                            content=c_content,
                            content_type=ChunkContentType.CODE_BLOCK,
                            headings=block.headings,
                            page=block.page,
                            section=block.section,
                            section_id=block.section_id,
                            start_line=s_line or block.start_line,
                            end_line=e_line or block.end_line,
                            user_id=user_id,
                            project_id=project_id,
                            source_type=parsed_doc.source_type,
                            source_url=source_url,
                            file_path=file_path or block.extra_metadata.get("file_path"),
                            commit_hash=commit_hash,
                            freshness=freshness,
                            trust_tier=trust_tier,
                        )
                    )
                    chunk_idx += 1
                i += 1
                continue

            # 2. Tables: Keep whole unless exceeding max_chunk_chars
            if block.content_type == ChunkContentType.TABLE:
                chunks.append(
                    self._build_chunk(
                        chunk_id=f"{parsed_doc.document_id}_chk_{chunk_idx}",
                        document_id=parsed_doc.document_id,
                        content=block.content,
                        content_type=ChunkContentType.TABLE,
                        headings=block.headings,
                        page=block.page,
                        section=block.section,
                        section_id=block.section_id,
                        user_id=user_id,
                        project_id=project_id,
                        source_type=parsed_doc.source_type,
                        source_url=source_url,
                        file_path=file_path,
                        commit_hash=commit_hash,
                        freshness=freshness,
                        trust_tier=trust_tier,
                    )
                )
                chunk_idx += 1
                i += 1
                continue

            # 3. Headings, Paragraphs, Lists: Merge sibling blocks under the same section up to target size
            merged_content: list[str] = [block.content]
            merged_headings = list(block.headings)
            current_section = block.section
            current_section_id = block.section_id
            current_page = block.page
            total_len = len(block.content)

            j = i + 1
            while j < len(blocks):
                next_block = blocks[j]
                # If next block is code or table, stop merging
                if next_block.content_type in {ChunkContentType.CODE_BLOCK, ChunkContentType.TABLE}:
                    break
                # If next block starts a new major section, stop merging
                if next_block.content_type == ChunkContentType.HEADING and total_len >= self.min_chunk_chars:
                    break
                # If adding next block exceeds target size, stop
                if total_len + len(next_block.content) > self.target_chunk_chars and total_len >= self.min_chunk_chars:
                    break

                merged_content.append(next_block.content)
                total_len += len(next_block.content)
                if not current_page and next_block.page:
                    current_page = next_block.page
                j += 1

            chunk_text = "\n\n".join(merged_content).strip()
            chunks.append(
                self._build_chunk(
                    chunk_id=f"{parsed_doc.document_id}_chk_{chunk_idx}",
                    document_id=parsed_doc.document_id,
                    content=chunk_text,
                    content_type=block.content_type,
                    headings=merged_headings,
                    page=current_page,
                    section=current_section,
                    section_id=current_section_id,
                    user_id=user_id,
                    project_id=project_id,
                    source_type=parsed_doc.source_type,
                    source_url=source_url,
                    file_path=file_path,
                    commit_hash=commit_hash,
                    freshness=freshness,
                    trust_tier=trust_tier,
                )
            )
            chunk_idx += 1
            i = j

        return chunks

    def _chunk_code_block(self, block: ParsedBlock) -> list[tuple[str, int | None, int | None]]:
        """Safely chunks oversized code blocks line by line without splitting single statements where possible."""
        text = block.content
        if len(text) <= self.max_chunk_chars:
            return [(text, block.start_line, block.end_line)]

        # Split on line boundaries
        lines = text.splitlines()
        segments: list[tuple[str, int | None, int | None]] = []
        cur_lines: list[str] = []
        cur_len = 0
        s_line = block.start_line or 1

        for idx, line in enumerate(lines):
            line_len = len(line) + 1
            if cur_len + line_len > self.target_chunk_chars and cur_lines:
                e_line = (s_line + len(cur_lines) - 1) if block.start_line else None
                segments.append(("\n".join(cur_lines), s_line if block.start_line else None, e_line))
                cur_lines = []
                cur_len = 0
                if block.start_line:
                    s_line = block.start_line + idx

            cur_lines.append(line)
            cur_len += line_len

        if cur_lines:
            e_line = (s_line + len(cur_lines) - 1) if block.start_line else None
            segments.append(("\n".join(cur_lines), s_line if block.start_line else None, e_line))

        return segments

    def _build_chunk(
        self,
        chunk_id: str,
        document_id: str,
        content: str,
        content_type: ChunkContentType,
        headings: list[str],
        page: int | None,
        section: str | None,
        section_id: str | None,
        user_id: str,
        project_id: str | None,
        source_type: RAGSourceType,
        source_url: str | None,
        file_path: str | None,
        commit_hash: str | None,
        freshness: FreshnessState,
        trust_tier: TrustTier,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> DocumentChunk:
        """Create DocumentChunk and calculate deterministic content hash."""
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        meta = ChunkMetadata(
            chunk_id=chunk_id,
            document_id=document_id,
            page=page,
            section=section,
            section_id=section_id,
            headings=headings,
            content_type=content_type,
            file_path=file_path,
            line_start=start_line,
            line_end=end_line,
            commit_hash=commit_hash,
            source_url=source_url,
            user_id=user_id,
            project_id=project_id,
            freshness=freshness,
            source_type=source_type,
            trust_tier=trust_tier,
        )

        return DocumentChunk(
            id=chunk_id,
            content=content,
            metadata=meta,
            content_hash=content_hash,
        )
