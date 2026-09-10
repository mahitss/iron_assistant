"""Document ingestion, multi-format parsing, structural chunking, and metadata extraction (Task 63)."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from app.research.safety import sanitize_research_directive
from app.research.schemas import Document, DocumentChunk, IngestDocumentRequest

logger = logging.getLogger(__name__)


class DocumentIngestionManager:
    """Ingests multi-format documents (Markdown, PDF, HTML, JSON, CSV, TXT) and performs structural semantic chunking.

    Invariant 9 & 10: Documents preserve provenance; chunking preserves headings, sections, and positions.
    Invariant 49 & 51: Document text is passive content; executable directives inside documents are neutralized.
    """

    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}

    def ingest(
        self,
        req_or_title: IngestDocumentRequest | str,
        content: str = "",
        source_id: str = "src_manual",
        format: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Convenience method accepting either IngestDocumentRequest or direct arguments."""
        if isinstance(req_or_title, IngestDocumentRequest):
            return self.ingest_document(
                title=req_or_title.title,
                content=req_or_title.content,
                source_id=req_or_title.source_id or "src_manual",
                format=req_or_title.format,
                metadata=req_or_title.metadata,
            )
        return self.ingest_document(
            title=req_or_title,
            content=content,
            source_id=source_id,
            format=format,
            metadata=metadata,
        )

    def ingest_text(
        self,
        content: str,
        source_id: str = "src_manual",
        title: str = "Document",
        format: str = "text",
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Ingest plaintext directly with source binding."""
        return self.ingest_document(
            title=title,
            content=content,
            source_id=source_id,
            format=format,
            metadata=metadata,
        )

    def ingest_document(
        self,
        title: str,
        content: str,
        source_id: str,
        format: str = "markdown",
        metadata: dict[str, Any] | None = None,
    ) -> Document:
        """Ingest raw document, sanitize instructions/secrets, compute hash, and partition into structural chunks."""
        # Sanitize against prompt injections while preserving document content
        sanitized_content = sanitize_research_directive(content)
        content_hash = hashlib.sha256(sanitized_content.encode("utf-8")).hexdigest()

        doc = Document(
            source_id=source_id,
            title=title,
            format=format.lower(),
            raw_content=sanitized_content,
            content_hash=content_hash,
            metadata=metadata or {},
        )

        chunks = self._chunk_document(doc.document_id, sanitized_content, doc.format)
        doc.chunks = chunks

        self._documents[doc.document_id] = doc
        logger.info(
            "DOCUMENT_INGESTED: doc=%s source=%s format=%s chunks=%d hash=%s",
            doc.document_id,
            source_id,
            doc.format,
            len(chunks),
            content_hash[:12],
        )
        return doc

    def get_document(self, document_id: str) -> Document | None:
        """Retrieve document by ID."""
        return self._documents.get(document_id)

    def list_documents(self, source_id: str | None = None) -> list[Document]:
        """List ingested documents, optionally filtered by source."""
        if source_id:
            return [d for d in self._documents.values() if d.source_id == source_id]
        return list(self._documents.values())

    def _chunk_document(self, document_id: str, content: str, format: str) -> list[DocumentChunk]:
        """Partition content into semantic blocks (headings, sections, paragraphs, tables)."""
        chunks: list[DocumentChunk] = []

        if format in ("markdown", "md", "text", "txt"):
            chunks = self._chunk_markdown(document_id, content)
        elif format in ("json", "api"):
            chunks = self._chunk_json(document_id, content)
        elif format == "csv":
            chunks = self._chunk_csv(document_id, content)
        else:
            chunks = self._chunk_generic(document_id, content)

        return chunks

    def _chunk_markdown(self, document_id: str, content: str) -> list[DocumentChunk]:
        """Parse markdown structure by section headings and paragraphs."""
        chunks: list[DocumentChunk] = []
        lines = content.splitlines()
        current_section = "Introduction"
        current_lines: list[str] = []
        start_line = 1
        page = 1

        heading_re = re.compile(r"^(#{1,6})\s+(.+)$")

        for idx, line in enumerate(lines, start=1):
            match = heading_re.match(line.strip())
            if match:
                # Flush previous paragraph/section chunk if exists
                if current_lines:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append(
                            DocumentChunk(
                                document_id=document_id,
                                content=chunk_text,
                                section=current_section,
                                page=page,
                                start_line=start_line,
                                end_line=idx - 1,
                                chunk_type="section",
                            )
                        )
                    current_lines = []

                current_section = match.group(2).strip()
                start_line = idx
            else:
                current_lines.append(line)
                # Split large paragraphs (e.g. > 15 lines or blank line separation)
                if line.strip() == "" and len(current_lines) > 5:
                    chunk_text = "\n".join(current_lines).strip()
                    if chunk_text:
                        chunks.append(
                            DocumentChunk(
                                document_id=document_id,
                                content=chunk_text,
                                section=current_section,
                                page=page,
                                start_line=start_line,
                                end_line=idx,
                                chunk_type="paragraph",
                            )
                        )
                    current_lines = []
                    start_line = idx + 1

        # Flush remaining lines
        if current_lines:
            chunk_text = "\n".join(current_lines).strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        document_id=document_id,
                        content=chunk_text,
                        section=current_section,
                        page=page,
                        start_line=start_line,
                        end_line=len(lines),
                        chunk_type="section",
                    )
                )

        return chunks

    def _chunk_json(self, document_id: str, content: str) -> list[DocumentChunk]:
        """Chunk JSON payloads into structured property blocks."""
        chunks: list[DocumentChunk] = []
        try:
            import json

            data = json.loads(content)
            if isinstance(data, dict):
                for key, val in data.items():
                    val_str = json.dumps(val, indent=2)
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            content=f"{key}: {val_str}",
                            section=f"property:{key}",
                            chunk_type="json_property",
                        )
                    )
            elif isinstance(data, list):
                for idx, item in enumerate(data):
                    item_str = json.dumps(item, indent=2)
                    chunks.append(
                        DocumentChunk(
                            document_id=document_id,
                            content=f"Item[{idx}]: {item_str}",
                            section=f"index:{idx}",
                            chunk_type="json_array_item",
                        )
                    )
        except Exception:
            return self._chunk_generic(document_id, content)
        return chunks

    def _chunk_csv(self, document_id: str, content: str) -> list[DocumentChunk]:
        """Chunk CSV data by header row and row batches."""
        chunks: list[DocumentChunk] = []
        lines = [line for line in content.splitlines() if line.strip()]
        if not lines:
            return chunks

        header = lines[0]
        batch_size = 10
        for i in range(1, len(lines), batch_size):
            batch = lines[i : i + batch_size]
            table_text = f"Headers: {header}\n" + "\n".join(batch)
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    content=table_text,
                    section="table_rows",
                    start_line=i + 1,
                    end_line=i + len(batch),
                    chunk_type="table",
                )
            )
        return chunks

    def _chunk_generic(self, document_id: str, content: str) -> list[DocumentChunk]:
        """Fallback generic chunking by paragraph breaks."""
        chunks: list[DocumentChunk] = []
        paras = [p.strip() for p in content.split("\n\n") if p.strip()]
        for idx, p in enumerate(paras, start=1):
            chunks.append(
                DocumentChunk(
                    document_id=document_id,
                    content=p,
                    section=f"Paragraph {idx}",
                    chunk_type="paragraph",
                )
            )
        return chunks


document_ingestion_manager = DocumentIngestionManager()
DocumentIngester = DocumentIngestionManager
document_ingester = document_ingestion_manager
