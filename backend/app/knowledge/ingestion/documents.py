"""Document parser, security validator, and semantic chunking engine."""

import csv
import io
import json
import logging
import os
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.knowledge.models import (
    KnowledgeEdgeModel,
    KnowledgeIndexJobModel,
    KnowledgeNodeModel,
    KnowledgeSourceModel,
)
from app.knowledge.schemas import (
    DocumentUploadResponse,
    IndexJobStatus,
    KnowledgeRelationType,
    KnowledgeSourceType,
    KnowledgeType,
)
from app.memory.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider

logger = logging.getLogger("kairo.knowledge.documents")

ALLOWED_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".pdf", ".docx"}


class DocumentIngestionService:
    """Safely ingests, validates, chunks, and indexes user-provided documents."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.settings = get_settings()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.max_bytes = self.settings.KAIRO_KNOWLEDGE_INDEX_MAX_BYTES
        self.chunk_size = self.settings.KAIRO_KNOWLEDGE_CHUNK_SIZE
        self.chunk_overlap = self.settings.KAIRO_KNOWLEDGE_CHUNK_OVERLAP

    async def ingest_document(
        self,
        session: AsyncSession,
        user_id: str,
        filename: str,
        file_bytes: bytes,
        project_id: str | None = None,
    ) -> DocumentUploadResponse:
        """Ingest document: validate -> extract text -> chunk -> embed -> persist nodes."""
        # 1. Security & Validation Checks
        self._validate_document(filename, file_bytes)

        job_id = str(uuid.uuid4())
        doc_source_id = f"doc_{uuid.uuid4().hex[:12]}"

        # Record IndexJob as PROCESSING
        job = KnowledgeIndexJobModel(
            id=job_id,
            user_id=user_id,
            job_type="DOCUMENT_INGESTION",
            status=IndexJobStatus.PROCESSING.value,
        )
        session.add(job)
        await session.flush()

        try:
            # 2. Extract Text Content
            raw_text = self._extract_text(filename, file_bytes)
            if not raw_text.strip():
                raise ValueError(f"Document '{filename}' contains no readable text content.")

            # 3. Create Root Document Provenance Source
            source = KnowledgeSourceModel(
                user_id=user_id,
                source_type=KnowledgeSourceType.USER_EXPLICIT.value,
                source_id=doc_source_id,
                title=filename,
                project_id=project_id,
                confidence=1.0,
                meta={"filename": filename, "file_size": len(file_bytes)},
            )
            session.add(source)

            # 4. Generate Document Summary and Embedding
            summary = raw_text[:500].strip()
            doc_embedding = await self.embedding_provider.embed(summary)

            # 5. Create Parent Knowledge Node
            parent_node = KnowledgeNodeModel(
                user_id=user_id,
                type=KnowledgeType.DOCUMENT.value,
                source_id=doc_source_id,
                project_id=project_id,
                title=filename,
                summary=f"Document '{filename}': {summary[:200]}...",
                content=raw_text[:20000],  # Bounded content cache
                embedding=doc_embedding,
                status="ACTIVE",
                confidence=1.0,
                node_metadata={"filename": filename, "size_bytes": len(file_bytes)},
            )
            session.add(parent_node)
            await session.flush()

            # 6. Semantic Chunking
            chunks = self._chunk_text(raw_text)
            chunks_created = 0

            for idx, chunk in enumerate(chunks):
                chunk_id = f"{doc_source_id}_chunk_{idx + 1}"
                chunk_embedding = await self.embedding_provider.embed(chunk["text"])

                chunk_node = KnowledgeNodeModel(
                    user_id=user_id,
                    type=KnowledgeType.DOCUMENT.value,
                    source_id=chunk_id,
                    project_id=project_id,
                    title=f"{filename} [{chunk['section']}]",
                    summary=chunk["text"][:300],
                    content=chunk["text"],
                    embedding=chunk_embedding,
                    status="ACTIVE",
                    confidence=1.0,
                    node_metadata={
                        "parent_node_id": parent_node.id,
                        "section": chunk["section"],
                        "chunk_index": idx,
                    },
                )
                session.add(chunk_node)
                await session.flush()

                # Link Chunk to Parent Node via DERIVED_FROM edge
                edge = KnowledgeEdgeModel(
                    user_id=user_id,
                    source_node_id=chunk_node.id,
                    target_node_id=parent_node.id,
                    relation_type=KnowledgeRelationType.DERIVED_FROM.value,
                    confidence=1.0,
                    source="DOCUMENT_PARSER",
                )
                session.add(edge)
                chunks_created += 1

            # 7. Update Job Status to COMPLETE
            job.node_id = parent_node.id
            job.status = IndexJobStatus.COMPLETE.value
            await session.commit()

            return DocumentUploadResponse(
                job_id=job_id,
                document_id=parent_node.id,
                filename=filename,
                status=IndexJobStatus.COMPLETE,
                chunks_created=chunks_created,
                message=f"Document '{filename}' successfully ingested and indexed into {chunks_created} semantic chunks.",
            )

        except Exception as exc:
            logger.error("Document ingestion failed for '%s': %s", filename, exc)
            job.status = IndexJobStatus.FAILED.value
            job.error_message = str(exc)
            await session.commit()
            raise

    def _validate_document(self, filename: str, file_bytes: bytes) -> None:
        """Enforce strict file size, name, and extension checks."""
        # 1. Path traversal, directory separators, and null byte prevention (checked first)
        clean_name = os.path.basename(filename)
        if (
            clean_name != filename
            or ".." in filename
            or "\x00" in filename
            or "/" in filename
            or "\\" in filename
        ):
            raise ValueError("Malicious filename or path traversal sequence detected.")

        # 2. Size Limit
        if len(file_bytes) > self.max_bytes:
            raise ValueError(
                f"File size ({len(file_bytes)} bytes) exceeds maximum permitted limit of {self.max_bytes} bytes."
            )
        if len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        # 3. Extension check
        ext = os.path.splitext(clean_name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File extension '{ext}' is not permitted. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

    def _extract_text(self, filename: str, file_bytes: bytes) -> str:
        """Extract clean text content based on file extension."""
        ext = os.path.splitext(filename)[1].lower()

        if ext in (".txt", ".md"):
            return file_bytes.decode("utf-8", errors="replace")

        if ext == ".json":
            try:
                data = json.loads(file_bytes.decode("utf-8", errors="replace"))
                return json.dumps(data, indent=2)
            except Exception as exc:
                raise ValueError(f"Invalid JSON file: {exc}") from exc

        if ext == ".csv":
            try:
                text_stream = io.StringIO(file_bytes.decode("utf-8", errors="replace"))
                reader = csv.reader(text_stream)
                lines = []
                for i, row in enumerate(reader):
                    if i > 500:  # Bound CSV lines
                        lines.append("... [truncated]")
                        break
                    lines.append(" | ".join(row))
                return "\n".join(lines)
            except Exception as exc:
                raise ValueError(f"Invalid CSV file: {exc}") from exc

        if ext == ".pdf":
            # PDF text extraction with resilient fallback
            try:
                import pypdf

                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                pages = [p.extract_text() or "" for p in reader.pages[:50]]
                return "\n\n".join(pages)
            except Exception:
                # Fallback to basic ascii stream extraction if pypdf unavailable
                text = re.sub(r"[^\x20-\x7E\n\t]", "", file_bytes.decode("latin1", errors="ignore"))
                return text[:10000]

        if ext == ".docx":
            # DOCX text extraction
            try:
                import docx

                doc = docx.Document(io.BytesIO(file_bytes))
                return "\n\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            except Exception:
                # Simple fallback
                return file_bytes.decode("utf-8", errors="ignore")[:10000]

        return file_bytes.decode("utf-8", errors="replace")

    def _chunk_text(self, text: str) -> list[dict[str, str]]:
        """Split text into semantic bounded chunks respecting markdown headings and paragraphs."""
        lines = text.split("\n")
        chunks: list[dict[str, str]] = []
        current_section = "Introduction"
        current_buffer: list[str] = []
        current_len = 0

        heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$")

        for line in lines:
            h_match = heading_pattern.match(line.strip())
            if h_match:
                # Flush previous buffer if large enough
                if current_len >= 150:
                    joined = "\n".join(current_buffer).strip()
                    if len(joined) >= 50:
                        chunks.append({"section": current_section, "text": joined})
                    current_buffer = []
                    current_len = 0
                current_section = h_match.group(2).strip()

            current_buffer.append(line)
            current_len += len(line) + 1

            if current_len >= self.chunk_size:
                joined = "\n".join(current_buffer).strip()
                if len(joined) >= 50:
                    chunks.append({"section": current_section, "text": joined})
                # Retain overlap
                current_buffer = current_buffer[-3:] if len(current_buffer) > 3 else []
                current_len = sum(len(line) for line in current_buffer)

        if current_buffer:
            joined = "\n".join(current_buffer).strip()
            if len(joined) >= 50:
                chunks.append({"section": current_section, "text": joined})

        return chunks if chunks else [{"section": "Document Content", "text": text[: self.chunk_size]}]
