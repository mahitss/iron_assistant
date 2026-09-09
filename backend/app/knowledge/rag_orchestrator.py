"""Central orchestrator for Kairo RAG V2 and Knowledge Fabric."""

import asyncio
import logging
import uuid
from typing import Any

from app.knowledge.chunking.semantic_chunker import SemanticChunker
from app.knowledge.cross_boundary.federated_retriever import FederatedKnowledgeBridge
from app.knowledge.generation.citation_engine import CitationEngine
from app.knowledge.governance.governance_filter import KnowledgeGovernanceFilter
from app.knowledge.graph.knowledge_graph import KnowledgeGraph
from app.knowledge.indexing.code_indexer import CodeSymbolIndex
from app.knowledge.indexing.embedding_pipeline import EmbeddingPipeline
from app.knowledge.indexing.lexical_index import LexicalIndex
from app.knowledge.indexing.vector_index import VectorIndex
from app.knowledge.ingestion.pipeline import IngestionPipeline
from app.knowledge.learning.retrieval_evaluator import RetrievalEvaluator
from app.knowledge.reranking.reranker import ReRanker
from app.knowledge.retrieval.hybrid_ranker import HybridRanker
from app.knowledge.retrieval.retrieval_planner import RetrievalPlanner
from app.knowledge.schemas import (
    ClassificationLevel,
    DocumentChunk,
    FreshnessState,
    HallucinationReport,
    IngestionJob,
    ParsedDocument,
    RAGSourceType,
    RetrievalPlan,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    TrustTier,
)

logger = logging.getLogger("kairo.knowledge.orchestrator")


class RAGOrchestrator:
    """End-to-end coordinator for multimodal ingestion, hybrid search, graph enrichment, governance, and citation verification."""

    def __init__(
        self,
        embedding_pipeline: EmbeddingPipeline | None = None,
        lexical_index: LexicalIndex | None = None,
        vector_index: VectorIndex | None = None,
        code_index: CodeSymbolIndex | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        governance_filter: KnowledgeGovernanceFilter | None = None,
        federated_bridge: FederatedKnowledgeBridge | None = None,
        evaluator: RetrievalEvaluator | None = None,
    ) -> None:
        self.ingestion = IngestionPipeline()
        self.chunker = SemanticChunker()
        self.embedding = embedding_pipeline or EmbeddingPipeline()
        self.lexical_index = lexical_index or LexicalIndex()
        self.vector_index = vector_index or VectorIndex(vector_dim=self.embedding.vector_dim)
        self.code_index = code_index or CodeSymbolIndex()
        self.planner = RetrievalPlanner()
        self.hybrid_ranker = HybridRanker()
        self.reranker = ReRanker()
        self.knowledge_graph = knowledge_graph or KnowledgeGraph()
        self.citation_engine = CitationEngine()
        self.governance = governance_filter or KnowledgeGovernanceFilter()
        self.federated = federated_bridge or FederatedKnowledgeBridge()
        self.evaluator = evaluator or RetrievalEvaluator()

        self._all_chunks: dict[str, DocumentChunk] = {}
        self._all_documents: dict[str, ParsedDocument] = {}

    async def ingest_content(
        self,
        raw_bytes: bytes,
        filename: str,
        content_type: str = "text/plain",
        source_type: RAGSourceType = RAGSourceType.USER_UPLOAD,
        classification: ClassificationLevel = ClassificationLevel.INTERNAL,
        trust_tier: TrustTier = TrustTier.USER_PROVIDED,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> IngestionJob:
        """Parse, chunk, index, extract entities, and register a new document."""
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        job = IngestionJob(
            job_id=job_id,
            document_id="",
            filename=filename,
            status="processing",
        )

        try:
            # 1. Parse document
            doc = await self.ingestion.parse_bytes(raw_bytes, filename, content_type)
            doc.source_type = source_type
            doc.classification = classification
            doc.trust_tier = trust_tier
            doc.project_id = project_id
            doc.user_id = user_id

            job.document_id = doc.document_id
            self._all_documents[doc.document_id] = doc

            # 2. Chunk document
            chunks = self.chunker.chunk_document(doc)

            # 3. Code symbol indexing if applicable
            if filename.endswith((".py", ".js", ".ts", ".jsx", ".tsx")):
                for c in chunks:
                    self.code_index.index_chunk(c)

            # 4. Generate embeddings
            texts = [c.content for c in chunks]
            embeddings = await self.embedding.embed_batch(texts)

            # 5. Populate indices
            for c, emb in zip(chunks, embeddings):
                c.embedding = emb
                self._all_chunks[c.id] = c
                self.lexical_index.index_chunk(c)
                self.vector_index.add_chunk(c, emb)

                # 6. Extract graph entities & relations
                self.knowledge_graph.extract_and_link_entities(c.content, chunk_id=c.id)

            job.status = "completed"
            job.chunks_created = len(chunks)
            logger.info("Successfully ingested %s into %d chunks (Job: %s)", filename, len(chunks), job_id)
        except Exception as exc:
            logger.exception("Failed ingestion for %s: %s", filename, exc)
            job.status = "failed"
            job.error_message = str(exc)

        return job

    async def retrieve_and_ground(self, request: RetrievalRequest) -> RetrievalResponse:
        """Execute end-to-end hybrid retrieval, governance filtering, graph enrichment, and context formatting."""
        # 1. Plan retrieval strategy
        plan = self.planner.plan(request)

        # Dynamic weight tuning from evaluator
        learned_bm25, learned_vec = self.evaluator.get_current_weights()
        plan.bm25_weight = (plan.bm25_weight + learned_bm25) / 2.0
        plan.vector_weight = (plan.vector_weight + learned_vec) / 2.0

        # 2. Dense search
        dense_candidates: list[tuple[DocumentChunk, float]] = []
        if plan.vector_weight > 0.05:
            q_emb = await self.embedding.embed_text(request.query)
            filter_meta = {}
            if request.project_id:
                filter_meta["project_id"] = request.project_id
            dense_candidates = self.vector_index.search(
                q_emb,
                top_k=plan.target_limit * 3,
                filter_metadata=filter_meta,
            )

        # 3. Lexical search (BM25)
        lexical_candidates: list[tuple[DocumentChunk, float]] = []
        if plan.bm25_weight > 0.05:
            lexical_candidates = self.lexical_index.search(
                request.query,
                top_k=plan.target_limit * 3,
            )

        # 4. Code symbol search if applicable
        code_candidates: list[DocumentChunk] = []
        if plan.code_symbol_weight > 0.1:
            code_candidates = self.code_index.search(request.query)

        # 5. Hybrid fusion and multi-factor ranking
        fused_results = self.hybrid_ranker.fuse_and_rank(
            bm25_results=lexical_candidates,
            vector_results=dense_candidates,
            plan=plan,
            code_matches=code_candidates,
        )

        # 6. Re-ranking with MMR diversity
        reranked_results = self.reranker.rerank(
            query=request.query,
            candidates=fused_results,
            top_k=plan.target_limit * 2,
        )

        # 7. Federated cross-boundary enrichment (Memory / Projects / World Model)
        if request.user_id:
            mem_chunks = await self.federated.fetch_memory_chunks(request.query, request.user_id, limit=2)
            for mc in mem_chunks:
                reranked_results.append(
                    RetrievalResult(
                        chunk=mc,
                        score=0.85,
                        citation_label="[Memory] User Profile & Preferences",
                    )
                )

        if request.project_id:
            proj_chunks = await self.federated.fetch_project_chunks(request.query, request.project_id, limit=2)
            for pc in proj_chunks:
                reranked_results.append(
                    RetrievalResult(
                        chunk=pc,
                        score=0.88,
                        citation_label=f"[Project Artifact] {pc.metadata.section}",
                    )
                )

        # 8. Governance & Security Filtering (RBAC, Clearance, Poisoning check)
        approved_results = self.governance.filter_chunks(
            results=reranked_results,
            user_id=request.user_id or "anonymous",
            user_role="admin" if (request.clearance == ClassificationLevel.RESTRICTED) else "member",
            user_clearance=request.clearance,
            allow_stale=request.allow_stale,
        )
        final_top = approved_results[: request.top_k]

        # 9. Knowledge Graph Enrichment
        graph_entities = []
        graph_relations = []
        # Find entities matching query
        for token in request.query.split():
            node = self.knowledge_graph.get_node(token)
            if node:
                nodes, edges = self.knowledge_graph.expand_neighborhood(node.name, max_depth=1)
                graph_entities.extend(nodes)
                graph_relations.extend(edges)

        # Deduplicate graph entities and relations
        seen_n = set()
        dedup_nodes = []
        for n in graph_entities:
            if n.name not in seen_n:
                seen_n.add(n.name)
                dedup_nodes.append(n)

        graph_context = self.knowledge_graph.format_subgraph_context(dedup_nodes, graph_relations)

        # 10. Format grounded context with numbered citations
        formatted_context, citations = self.citation_engine.format_context(
            results=final_top,
            max_tokens=request.max_tokens,
        )

        if graph_context:
            formatted_context = f"{formatted_context}\n\n{graph_context}"

        # 11. Record evaluation telemetry
        self.evaluator.record_event(
            query=request.query,
            results=final_top,
            grounding_score=1.0,
        )

        return RetrievalResponse(
            query=request.query,
            results=final_top,
            formatted_context=formatted_context,
            citations=citations,
            plan=plan,
            total_found=len(fused_results),
        )

    def verify_answer(
        self,
        generated_answer: str,
        citations: list[dict[str, Any]],
        results: list[RetrievalResult],
    ) -> HallucinationReport:
        """Validate answer against source citations."""
        return self.citation_engine.verify_generation(
            generated_text=generated_answer,
            citation_manifest=citations,
            results=results,
        )

    def record_feedback(self, query: str, feedback: float, results: list[RetrievalResult]) -> None:
        """Log user thumbs-up (+1.0) or thumbs-down (-1.0)."""
        self.evaluator.record_event(query=query, results=results, user_feedback=feedback)

    def get_eval_metrics(self) -> Any:
        return self.evaluator.compute_metrics()

    def get_stats(self) -> dict[str, Any]:
        """Aggregate stats across all indices and graphs."""
        return {
            "total_documents": len(self._all_documents),
            "total_chunks": len(self._all_chunks),
            "lexical_index_size": self.lexical_index.total_chunks(),
            "vector_index_size": self.vector_index.total_chunks(),
            "code_symbols_count": self.code_index.total_symbols(),
            "graph_nodes": self.knowledge_graph.total_nodes(),
            "graph_edges": self.knowledge_graph.total_edges(),
            "quarantined_count": len(self.governance.get_quarantined_records()),
        }
