"""Document parsing engine extracting structural blocks, hierarchies, tables, equations, and code."""

import csv
import io
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.knowledge.schemas import ChunkContentType, RAGSourceType

logger = logging.getLogger("kairo.knowledge.parsing")


@dataclass
class ParsedBlock:
    """A structurally parsed segment of a document."""

    block_id: str
    content: str
    content_type: ChunkContentType
    headings: list[str] = field(default_factory=list)
    page: int | None = None
    section: str | None = None
    section_id: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    language: str | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Complete structured representation of a parsed document."""

    document_id: str
    title: str
    source_type: RAGSourceType
    blocks: list[ParsedBlock]
    total_blocks: int
    raw_character_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


class DocumentParser:
    """Universal parser for Markdown, PDFs, code repositories, web content, transcripts, and structured data."""

    def parse(
        self,
        content: str | bytes,
        filename: str = "document.txt",
        source_type: RAGSourceType | None = None,
        document_id: str | None = None,
        title: str | None = None,
        user_metadata: dict[str, Any] | None = None,
    ) -> ParsedDocument:
        """Parse raw content into structured blocks with heading hierarchy and positional metadata."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        meta = user_metadata or {}
        ext = self._get_extension(filename)

        # Convert bytes to string if needed
        if isinstance(content, bytes):
            text = self._decode_bytes(content, ext)
        else:
            text = content

        inferred_type = source_type or self._infer_source_type(filename, ext)
        inferred_title = title or self._extract_title(text, filename)

        blocks: list[ParsedBlock] = []

        if ext in {".md", ".markdown"}:
            blocks = self._parse_markdown(text, doc_id)
        elif ext == ".pdf":
            blocks = self._parse_pdf_text(text, doc_id)
        elif ext in {".py", ".ts", ".js", ".go", ".rs", ".java", ".cpp", ".c", ".sql"}:
            blocks = self._parse_code_file(text, doc_id, ext)
        elif ext == ".csv":
            blocks = self._parse_csv(text, doc_id)
        elif ext in {".json", ".jsonl"}:
            blocks = self._parse_json(text, doc_id)
        elif ext in {".yaml", ".yml"}:
            blocks = self._parse_yaml(text, doc_id)
        elif ext in {".html", ".htm"}:
            blocks = self._parse_html(text, doc_id)
        else:
            blocks = self._parse_generic_text(text, doc_id)

        # Fallback if no blocks produced
        if not blocks and text.strip():
            blocks = [
                ParsedBlock(
                    block_id=f"{doc_id}_blk_0",
                    content=text.strip(),
                    content_type=ChunkContentType.PARAGRAPH,
                    headings=[inferred_title],
                    section=inferred_title,
                )
            ]

        return ParsedDocument(
            document_id=doc_id,
            title=inferred_title,
            source_type=inferred_type,
            blocks=blocks,
            total_blocks=len(blocks),
            raw_character_count=len(text),
            metadata=meta,
        )

    def _get_extension(self, filename: str) -> str:
        idx = filename.rfind(".")
        return filename[idx:].lower() if idx != -1 else ""

    def _decode_bytes(self, data: bytes, ext: str) -> str:
        # If PDF binary, try basic text extraction or utf-8 fallback
        if ext == ".pdf":
            try:
                # Basic text stream extraction from uncompressed PDF streams
                decoded = data.decode("latin-1", errors="ignore")
                matches = re.findall(r"\((.*?)\)T[jJ]", decoded)
                if matches:
                    return "\n".join(matches)
            except Exception:
                pass
        return data.decode("utf-8", errors="replace")

    def _infer_source_type(self, filename: str, ext: str) -> RAGSourceType:
        if ext == ".pdf":
            return RAGSourceType.PDF
        if ext in {".md", ".markdown"}:
            return RAGSourceType.MARKDOWN
        if ext in {".py", ".ts", ".js", ".go", ".rs", ".sql"}:
            return RAGSourceType.CODE
        if ext in {".csv", ".json", ".yaml", ".yml"}:
            return RAGSourceType.STRUCTURED_DATA
        if "transcript" in filename.lower():
            return RAGSourceType.AUDIO_TRANSCRIPT
        return RAGSourceType.DOCUMENT

    def _extract_title(self, text: str, filename: str) -> str:
        # Try Markdown H1
        h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if h1_match:
            return h1_match.group(1).strip()
        # Fallback to base filename
        base = filename.split("/")[-1].split("\\")[-1]
        if "." in base:
            base = base.rsplit(".", 1)[0]
        return base.replace("_", " ").replace("-", " ").title()

    # --- Markdown Parsing ---

    def _parse_markdown(self, text: str, doc_id: str) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        lines = text.splitlines()
        current_headings: list[str] = []
        current_section = "Introduction"
        current_section_id = "sec_intro"
        buffer: list[str] = []
        block_counter = 0

        in_code_block = False
        code_lang = None
        code_buffer: list[str] = []
        start_line = 1

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Code fence toggle
            if stripped.startswith("```"):
                if in_code_block:
                    # End code block
                    code_content = "\n".join(code_buffer)
                    if code_content.strip():
                        blocks.append(
                            ParsedBlock(
                                block_id=f"{doc_id}_blk_{block_counter}",
                                content=f"```{code_lang or ''}\n{code_content}\n```",
                                content_type=ChunkContentType.CODE_BLOCK,
                                headings=list(current_headings),
                                section=current_section,
                                section_id=current_section_id,
                                start_line=start_line,
                                end_line=line_num,
                                language=code_lang,
                            )
                        )
                        block_counter += 1
                    in_code_block = False
                    code_buffer = []
                    code_lang = None
                    continue
                else:
                    # Flush pending buffer
                    if buffer:
                        self._flush_text_buffer(
                            buffer, blocks, doc_id, block_counter, current_headings, current_section, current_section_id
                        )
                        block_counter += len(blocks)
                        buffer = []
                    in_code_block = True
                    code_lang = stripped[3:].strip() or "text"
                    code_buffer = []
                    start_line = line_num
                    continue

            if in_code_block:
                code_buffer.append(line)
                continue

            # Heading match
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                if buffer:
                    self._flush_text_buffer(
                        buffer, blocks, doc_id, block_counter, current_headings, current_section, current_section_id
                    )
                    block_counter += len(blocks)
                    buffer = []

                level = len(heading_match.group(1))
                h_text = heading_match.group(2).strip()

                # Adjust hierarchy
                if level <= len(current_headings):
                    current_headings = current_headings[: level - 1]
                current_headings.append(h_text)
                current_section = h_text
                current_section_id = f"sec_{re.sub(r'[^a-zA-Z0-9]', '_', h_text.lower())[:32]}"

                blocks.append(
                    ParsedBlock(
                        block_id=f"{doc_id}_blk_{block_counter}",
                        content=stripped,
                        content_type=ChunkContentType.HEADING,
                        headings=list(current_headings),
                        section=current_section,
                        section_id=current_section_id,
                        start_line=line_num,
                        end_line=line_num,
                    )
                )
                block_counter += 1
                continue

            # Table row detection (| col1 | col2 |)
            if stripped.startswith("|") and stripped.endswith("|"):
                buffer.append(line)
                continue

            # Empty line indicates paragraph boundary
            if not stripped:
                if buffer:
                    self._flush_text_buffer(
                        buffer, blocks, doc_id, block_counter, current_headings, current_section, current_section_id
                    )
                    block_counter += len(blocks)
                    buffer = []
                continue

            buffer.append(line)

        # Flush any remaining buffer
        if buffer:
            self._flush_text_buffer(
                buffer, blocks, doc_id, block_counter, current_headings, current_section, current_section_id
            )

        return blocks

    def _flush_text_buffer(
        self,
        buffer: list[str],
        blocks: list[ParsedBlock],
        doc_id: str,
        counter: int,
        headings: list[str],
        section: str,
        section_id: str,
    ) -> None:
        content = "\n".join(buffer).strip()
        if not content:
            return

        c_type = ChunkContentType.PARAGRAPH
        if content.startswith("|") and "|" in content:
            c_type = ChunkContentType.TABLE
        elif re.match(r"^[-*+]\s|^\d+\.\s", content):
            c_type = ChunkContentType.LIST
        elif content.startswith("$$") or content.startswith("\\["):
            c_type = ChunkContentType.EQUATION

        blocks.append(
            ParsedBlock(
                block_id=f"{doc_id}_blk_{counter}",
                content=content,
                content_type=c_type,
                headings=list(headings),
                section=section,
                section_id=section_id,
            )
        )

    # --- PDF Text Parsing with Page Markers ---

    def _parse_pdf_text(self, text: str, doc_id: str) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        # Look for page markers like --- Page 1 --- or Page 1 of N or form feeds \x0c
        page_splits = re.split(r"(?:--- Page (\d+) ---|\x0c|\[Page (\d+)\])", text)
        current_page = 1
        counter = 0

        # Handle splitting with regex captures
        segments: list[tuple[int, str]] = []
        i = 0
        while i < len(page_splits):
            seg = page_splits[i]
            if seg is None:
                i += 1
                continue
            if seg.isdigit():
                current_page = int(seg)
                i += 1
                if i < len(page_splits) and page_splits[i]:
                    segments.append((current_page, page_splits[i]))
            else:
                segments.append((current_page, seg))
            i += 1

        for page_num, seg in segments:
            paragraphs = [p.strip() for p in seg.split("\n\n") if p.strip()]
            for p in paragraphs:
                # Heading heuristic: short line without ending punctuation
                c_type = ChunkContentType.PARAGRAPH
                if len(p) < 80 and not p.endswith((".", ":", ";", "?", "!")) and "\n" not in p:
                    c_type = ChunkContentType.HEADING
                blocks.append(
                    ParsedBlock(
                        block_id=f"{doc_id}_blk_{counter}",
                        content=p,
                        content_type=c_type,
                        page=page_num,
                        section=f"Page {page_num}",
                        section_id=f"page_{page_num}",
                    )
                )
                counter += 1

        return blocks

    # --- Code Parsing ---

    def _parse_code_file(self, text: str, doc_id: str, ext: str) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        lines = text.splitlines()
        lang = ext.lstrip(".")

        # In code files, extract class/function boundaries
        buffer: list[str] = []
        current_symbol = "Module Level"
        start_line = 1
        counter = 0

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Detect top-level def / class in python
            is_new_symbol = False
            if ext == ".py":
                if line.startswith("def ") or line.startswith("class ") or line.startswith("async def "):
                    is_new_symbol = True
            elif ext in {".ts", ".js"}:
                if (
                    line.startswith("function ")
                    or line.startswith("class ")
                    or line.startswith("export function ")
                    or line.startswith("export class ")
                    or line.startswith("const ")
                    and "=>" in line
                ):
                    is_new_symbol = True

            if is_new_symbol and buffer:
                content = "\n".join(buffer).strip()
                if content:
                    blocks.append(
                        ParsedBlock(
                            block_id=f"{doc_id}_blk_{counter}",
                            content=content,
                            content_type=ChunkContentType.CODE_BLOCK,
                            headings=[current_symbol],
                            section=current_symbol,
                            section_id=f"sym_{counter}",
                            start_line=start_line,
                            end_line=line_num - 1,
                            language=lang,
                        )
                    )
                    counter += 1
                buffer = []
                start_line = line_num
                current_symbol = stripped.split("(")[0].split(":")[0].strip()

            buffer.append(line)

        if buffer:
            content = "\n".join(buffer).strip()
            if content:
                blocks.append(
                    ParsedBlock(
                        block_id=f"{doc_id}_blk_{counter}",
                        content=content,
                        content_type=ChunkContentType.CODE_BLOCK,
                        headings=[current_symbol],
                        section=current_symbol,
                        section_id=f"sym_{counter}",
                        start_line=start_line,
                        end_line=len(lines),
                        language=lang,
                    )
                )

        return blocks

    # --- Structured Data Parsing (CSV, JSON, YAML) ---

    def _parse_csv(self, text: str, doc_id: str) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return blocks

        header = rows[0]
        header_str = ", ".join(header)
        counter = 0

        # Group into 10-row tabular batches
        batch_size = 10
        for i in range(1, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            formatted_rows = [f"Header: [{header_str}]"]
            for r in batch:
                formatted_rows.append(" | ".join(r))
            blocks.append(
                ParsedBlock(
                    block_id=f"{doc_id}_blk_{counter}",
                    content="\n".join(formatted_rows),
                    content_type=ChunkContentType.TABLE,
                    headings=["CSV Dataset", f"Rows {i} to {min(i + batch_size - 1, len(rows) - 1)}"],
                    section=f"Rows {i}-{i+len(batch)-1}",
                    section_id=f"csv_batch_{counter}",
                )
            )
            counter += 1
        return blocks

    def _parse_json(self, text: str, doc_id: str) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for idx, item in enumerate(data[:50]):
                    blocks.append(
                        ParsedBlock(
                            block_id=f"{doc_id}_blk_{idx}",
                            content=json.dumps(item, indent=2),
                            content_type=ChunkContentType.STRUCTURED_ROW,
                            headings=[f"Item {idx + 1}"],
                            section=f"Item {idx + 1}",
                            section_id=f"json_item_{idx}",
                        )
                    )
            elif isinstance(data, dict):
                for key, val in data.items():
                    blocks.append(
                        ParsedBlock(
                            block_id=f"{doc_id}_blk_{key}",
                            content=f"{key}:\n{json.dumps(val, indent=2)}",
                            content_type=ChunkContentType.STRUCTURED_ROW,
                            headings=[str(key)],
                            section=str(key),
                            section_id=f"json_key_{key}",
                        )
                    )
        except Exception:
            return self._parse_generic_text(text, doc_id)
        return blocks

    def _parse_yaml(self, text: str, doc_id: str) -> list[ParsedBlock]:
        # Split on top-level yaml documents (---)
        docs = text.split("\n---")
        blocks: list[ParsedBlock] = []
        for idx, doc in enumerate(docs):
            if doc.strip():
                blocks.append(
                    ParsedBlock(
                        block_id=f"{doc_id}_blk_{idx}",
                        content=doc.strip(),
                        content_type=ChunkContentType.STRUCTURED_ROW,
                        headings=[f"YAML Document {idx + 1}"],
                        section=f"Doc {idx + 1}",
                        section_id=f"yaml_doc_{idx}",
                    )
                )
        return blocks

    def _parse_html(self, text: str, doc_id: str) -> list[ParsedBlock]:
        # Strip script/style tags and clean HTML
        clean = re.sub(r"<(script|style).*?</\1>", "", text, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r"<[^>]+>", "\n", clean)
        clean = re.sub(r"\n{2,}", "\n\n", clean)
        return self._parse_generic_text(clean.strip(), doc_id)

    def _parse_generic_text(self, text: str, doc_id: str) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        for idx, p in enumerate(paragraphs):
            blocks.append(
                ParsedBlock(
                    block_id=f"{doc_id}_blk_{idx}",
                    content=p,
                    content_type=ChunkContentType.PARAGRAPH,
                    headings=["General"],
                    section="Body",
                    section_id=f"p_{idx}",
                )
            )
        return blocks
