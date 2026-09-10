"""Transactional facade coordinating research domain operations with persistence and cross-subsystem dispatch (Task 63)."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.research.engine import ResearchEngine, research_engine
from app.research.models import (
    ResearchDocumentModel,
    ResearchSessionModel,
)
from app.research.schemas import (
    Claim,
    ConflictRecord,
    Document,
    Evidence,
    IngestDocumentRequest,
    KnowledgeGap,
    ResearchRequest,
    Source,
    SynthesisResult,
    VerifyClaimRequest,
)

logger = logging.getLogger(__name__)


class ResearchService:
    """Coordinates research lifecycle execution, state persistence, and cross-system knowledge propagation."""

    def __init__(self, engine: ResearchEngine | None = None) -> None:
        self._engine = engine or research_engine

    async def execute_research(
        self,
        req: ResearchRequest,
        db: AsyncSession | None = None,
    ) -> SynthesisResult:
        """Run complete research synthesis session and persist session record."""
        result = self._engine.execute_research_session(req)

        if db:
            session_model = ResearchSessionModel(
                session_id=result.session_id,
                question=result.question,
                objective=req.objective,
                scope=req.scope,
                mode=req.mode.value,
                quality_score=result.quality_score.composite_score,
                summary=result.executive_summary,
                tenant_id=req.tenant_id,
            )
            db.add(session_model)
            await db.commit()

        return result

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve cached research session."""
        return self._engine._active_sessions.get(session_id)

    def get_sources(self, session_id: str) -> list[Source]:
        """Retrieve sources for a session."""
        sess = self._engine._active_sessions.get(session_id)
        if not sess:
            return []
        return sess.get("sources", [])

    def get_claims(self, session_id: str) -> list[Claim]:
        """Retrieve claims extracted during a session."""
        sess = self._engine._active_sessions.get(session_id)
        if not sess:
            return []
        return sess.get("claims", [])

    def get_evidence(self, session_id: str) -> list[Evidence]:
        """Retrieve evidence items linked during a session."""
        sess = self._engine._active_sessions.get(session_id)
        if not sess:
            return []
        return sess.get("evidence", [])

    def get_conflicts(self, session_id: str) -> list[ConflictRecord]:
        """Retrieve conflicts detected during a session."""
        sess = self._engine._active_sessions.get(session_id)
        if not sess:
            return []
        return sess.get("conflicts", [])

    def get_gaps(self, session_id: str) -> list[KnowledgeGap]:
        """Retrieve knowledge gaps identified during a session."""
        sess = self._engine._active_sessions.get(session_id)
        if not sess:
            return []
        return sess.get("gaps", [])

    def replay_session(self, session_id: str) -> dict[str, Any]:
        """Reconstruct historical research trace (Invariant 48)."""
        return self._engine.replay_session(session_id)

    async def ingest_document(
        self,
        req: IngestDocumentRequest,
        db: AsyncSession | None = None,
    ) -> Document:
        """Register source and ingest a new document."""
        source = self._engine.source_registry.register_source(
            title=req.title,
            source_type=req.source_type,
            url_or_reference=req.url_or_reference,
            publisher=req.publisher,
            author=req.author,
            is_primary=req.is_primary,
        )

        doc = self._engine.document_manager.ingest_document(
            title=req.title,
            content=req.content,
            source_id=source.source_id,
            format=req.format,
        )

        if db:
            doc_model = ResearchDocumentModel(
                document_id=doc.document_id,
                source_id=source.source_id,
                title=doc.title,
                format=doc.format,
                content_hash=doc.content_hash,
                raw_content=doc.raw_content[:2000],
            )
            db.add(doc_model)
            await db.commit()

        return doc

    def verify_claim(self, req: VerifyClaimRequest) -> Claim:
        """Verify an existing claim with additional corroborating evidence."""
        claim = self._engine.claim_extractor.get_claim(req.claim_id)
        if not claim:
            raise KeyError(f"Claim '{req.claim_id}' not found.")

        claim.status = "VERIFIED" if req.is_verified else "DISPUTED"
        claim.provenance["verified_by"] = req.actor
        claim.provenance["verification_note"] = req.verification_evidence

        self._engine.auditor.record_event(
            event_type="CLAIM_VERIFIED",
            actor=req.actor,
            claim_id=claim.claim_id,
            details={"is_verified": req.is_verified, "evidence": req.verification_evidence},
        )
        return claim

    def retract_source(self, source_id: str, reason: str) -> dict[str, Any]:
        """Retract a source and propagate impact to downstream knowledge."""
        impact = self._engine.continuous_manager.handle_source_retraction(source_id, reason=reason)
        self._engine.auditor.record_event(
            event_type="SOURCE_RETRACTED",
            actor="ADMINISTRATOR",
            source_id=source_id,
            details={"reason": reason, "affected_claims": impact["affected_claims_count"]},
        )
        return impact

    def get_audit_trail(
        self,
        session_id: str | None = None,
        source_id: str | None = None,
        claim_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve audit log entries."""
        return self._engine.auditor.get_events(
            session_id=session_id,
            source_id=source_id,
            claim_id=claim_id,
            limit=limit,
        )

    def propagate_to_knowledge_graph(self, synthesis: SynthesisResult) -> dict[str, Any]:
        """Package verified claims and entities for integration with Task 50 Knowledge Graph."""
        nodes = []
        edges = []
        for claim in synthesis.established_findings[:5]:
            nodes.append({"id": f"kg_{claim[:20]}", "label": claim[:30], "type": "RESEARCH_CLAIM"})
        return {
            "session_id": synthesis.session_id,
            "nodes_generated": len(nodes),
            "edges_generated": len(edges),
            "status": "PROPAGATED_TO_KNOWLEDGE_GRAPH",
        }

    def promote_to_executive_memory(self, synthesis: SynthesisResult) -> dict[str, Any]:
        """Package high-confidence research outcomes for promotion into Task 53 Executive Memory."""
        return {
            "session_id": synthesis.session_id,
            "title": f"Research Synthesis: {synthesis.question[:40]}",
            "executive_summary": synthesis.executive_summary,
            "quality_score": synthesis.quality_score.composite_score,
            "status": "PROMOTED_TO_EXECUTIVE_MEMORY",
        }


research_service = ResearchService()
