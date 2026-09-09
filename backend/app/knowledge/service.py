"""KnowledgeFabricService: Central coordinator for knowledge nodes, edges, decisions, provenance, and audit."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.knowledge.graph import GraphTraversalService
from app.knowledge.models import (
    KnowledgeEdgeModel,
    KnowledgeNodeModel,
    KnowledgeSourceModel,
)
from app.knowledge.schemas import (
    DecisionCreate,
    DecisionResponse,
    DecisionStatus,
    KnowledgeEdgeCreate,
    KnowledgeEdgeResponse,
    KnowledgeNodeCreate,
    KnowledgeNodeResponse,
    KnowledgeNodeUpdate,
    KnowledgeRelationType,
    KnowledgeSearchRequest,
    KnowledgeSearchResultItem,
    KnowledgeSourceResponse,
    KnowledgeSourceType,
    KnowledgeType,
)
from app.knowledge.search import HybridSearchEngine
from app.knowledge.temporal import TemporalReasoner
from app.memory.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider
from app.security.audit import AuditLogger

logger = logging.getLogger("kairo.knowledge.service")


class KnowledgeFabricService:
    """Authoritative service orchestrating the Kairo Knowledge Fabric."""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        redis_client: Any | None = None,
        search_engine: HybridSearchEngine | None = None,
        traversal_service: GraphTraversalService | None = None,
        temporal_reasoner: TemporalReasoner | None = None,
    ) -> None:
        self.settings = get_settings()
        self.embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self.search_engine = search_engine or HybridSearchEngine(
            embedding_provider=self.embedding_provider, redis_client=redis_client
        )
        self.traversal_service = traversal_service or GraphTraversalService(
            max_depth=self.settings.KAIRO_KNOWLEDGE_MAX_DEPTH,
            max_nodes=self.settings.KAIRO_KNOWLEDGE_MAX_NODES,
            max_edges=self.settings.KAIRO_KNOWLEDGE_MAX_EDGES,
        )
        self.temporal_reasoner = temporal_reasoner or TemporalReasoner()

    # --- Node Operations ---

    async def create_node(
        self, session: AsyncSession, user_id: str, node_in: KnowledgeNodeCreate
    ) -> KnowledgeNodeResponse:
        """Create and embed a new knowledge node with provenance tracking."""
        # 1. Compute embedding if enabled
        emb_text = f"{node_in.title}\n{node_in.summary}"
        embedding = None
        try:
            embedding = await self.embedding_provider.embed(emb_text)
        except Exception as exc:
            logger.warning("Embedding generation failed for node '%s': %s", node_in.title, exc)

        node = KnowledgeNodeModel(
            user_id=user_id,
            type=node_in.type.value,
            source_id=node_in.source_id,
            project_id=node_in.project_id,
            title=node_in.title,
            summary=node_in.summary,
            content=node_in.content,
            embedding=embedding,
            status="ACTIVE",
            confidence=node_in.confidence,
            node_metadata=node_in.metadata,
        )
        session.add(node)
        await session.flush()

        # 2. Record provenance in knowledge_sources if not present
        src_stmt = select(KnowledgeSourceModel).where(
            and_(
                KnowledgeSourceModel.user_id == user_id,
                KnowledgeSourceModel.source_id == node_in.source_id,
            )
        )
        existing_src = (await session.execute(src_stmt)).scalar_one_or_none()
        if not existing_src:
            source = KnowledgeSourceModel(
                user_id=user_id,
                source_type=node_in.source_type.value,
                source_id=node_in.source_id,
                source_url=node_in.source_url,
                title=node_in.title,
                project_id=node_in.project_id,
                confidence=node_in.confidence,
            )
            session.add(source)

        await AuditLogger.log_event(
            db_session=session,
            user_id=user_id,
            event_type="knowledge.node_created",
            decision="ALLOWED",
            success=True,
            metadata={"type": node.type, "title": node.title, "source_id": node.source_id},
        )

        await session.commit()
        await self.search_engine.invalidate_cache(user_id)

        return KnowledgeNodeResponse.model_validate(node)

    async def get_node(
        self, session: AsyncSession, user_id: str, node_id: str
    ) -> KnowledgeNodeResponse | None:
        """Fetch node enforcing multi-tenant user ownership."""
        stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.id == node_id,
                KnowledgeNodeModel.user_id == user_id,
                KnowledgeNodeModel.status != "DELETED",
            )
        )
        res = await session.execute(stmt)
        node = res.scalar_one_or_none()
        if not node:
            return None
        return KnowledgeNodeResponse.model_validate(node)

    async def update_node(
        self, session: AsyncSession, user_id: str, node_id: str, update_in: KnowledgeNodeUpdate
    ) -> KnowledgeNodeResponse:
        """Update node fields and refresh cache."""
        stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.id == node_id,
                KnowledgeNodeModel.user_id == user_id,
                KnowledgeNodeModel.status != "DELETED",
            )
        )
        res = await session.execute(stmt)
        node = res.scalar_one_or_none()
        if not node:
            raise ValueError(f"Knowledge node '{node_id}' not found or access denied.")

        dump = update_in.model_dump(exclude_unset=True)
        for key, val in dump.items():
            if key == "metadata" and val is not None:
                current_meta = node.node_metadata or {}
                current_meta.update(val)
                node.node_metadata = current_meta
            elif hasattr(node, key) and val is not None:
                setattr(node, key, val)

        node.updated_at = datetime.now(UTC)
        await session.commit()
        await self.search_engine.invalidate_cache(user_id)

        return KnowledgeNodeResponse.model_validate(node)

    async def delete_node(self, session: AsyncSession, user_id: str, node_id: str) -> bool:
        """Mark node DELETED and cascade clean references to avoid dangling edges."""
        stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.id == node_id,
                KnowledgeNodeModel.user_id == user_id,
            )
        )
        res = await session.execute(stmt)
        node = res.scalar_one_or_none()
        if not node:
            return False

        # If it's a parent document, also soft delete its chunks
        if node.type == KnowledgeType.DOCUMENT.value:
            chunk_stmt = select(KnowledgeNodeModel).where(
                and_(
                    KnowledgeNodeModel.user_id == user_id,
                    KnowledgeNodeModel.source_id.like(f"{node.source_id}_chunk_%"),
                )
            )
            chunks = (await session.execute(chunk_stmt)).scalars().all()
            for chunk in chunks:
                chunk.status = "DELETED"

        node.status = "DELETED"
        node.updated_at = datetime.now(UTC)

        await AuditLogger.log_event(
            db_session=session,
            user_id=user_id,
            event_type="knowledge.node_deleted",
            decision="ALLOWED",
            success=True,
            metadata={"type": node.type, "title": node.title},
        )

        await session.commit()
        await self.search_engine.invalidate_cache(user_id)

        return True

    # --- Edge Operations ---

    async def create_edge(
        self, session: AsyncSession, user_id: str, edge_in: KnowledgeEdgeCreate
    ) -> KnowledgeEdgeResponse:
        """Create a typed relationship edge after strictly validating both endpoints and type."""
        # 1. Enforce relation type is an allowlisted enum member
        if not isinstance(edge_in.relation_type, KnowledgeRelationType):
            raise ValueError(f"Invalid relation type: {edge_in.relation_type}")

        # 2. Verify source node exists and belongs to user
        src_stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.id == edge_in.source_node_id,
                KnowledgeNodeModel.user_id == user_id,
            )
        )
        src_node = (await session.execute(src_stmt)).scalar_one_or_none()
        if not src_node:
            raise ValueError(f"Source node '{edge_in.source_node_id}' not found or access denied.")

        # 3. Verify target node exists and belongs to user
        tgt_stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.id == edge_in.target_node_id,
                KnowledgeNodeModel.user_id == user_id,
            )
        )
        tgt_node = (await session.execute(tgt_stmt)).scalar_one_or_none()
        if not tgt_node:
            raise ValueError(f"Target node '{edge_in.target_node_id}' not found or access denied.")

        edge = KnowledgeEdgeModel(
            user_id=user_id,
            source_node_id=edge_in.source_node_id,
            target_node_id=edge_in.target_node_id,
            relation_type=edge_in.relation_type.value,
            confidence=edge_in.confidence,
            source=edge_in.source,
        )
        session.add(edge)
        await session.commit()

        return KnowledgeEdgeResponse.model_validate(edge)

    # --- Decisions Operations ---

    async def record_decision(
        self, session: AsyncSession, user_id: str, decision_in: DecisionCreate
    ) -> DecisionResponse:
        """Record an explicit architectural or project decision as a DECISION knowledge node."""
        decision_id = f"dec_{uuid.uuid4().hex[:12]}"
        emb = await self.embedding_provider.embed(f"{decision_in.decision}\n{decision_in.rationale or ''}")

        node = KnowledgeNodeModel(
            user_id=user_id,
            type=KnowledgeType.DECISION.value,
            source_id=decision_id,
            project_id=decision_in.project_id,
            title=decision_in.decision,
            summary=decision_in.rationale or decision_in.decision,
            content=decision_in.rationale,
            embedding=emb,
            status=DecisionStatus.ACTIVE.value,
            confidence=1.0,
            node_metadata={"source": decision_in.source},
        )
        session.add(node)
        await session.flush()

        source = KnowledgeSourceModel(
            user_id=user_id,
            source_type=KnowledgeSourceType.USER_EXPLICIT.value,
            source_id=decision_id,
            title=decision_in.decision,
            project_id=decision_in.project_id,
            confidence=1.0,
        )
        session.add(source)

        # Link to project if specified
        if decision_in.project_id:
            proj_stmt = select(KnowledgeNodeModel).where(
                and_(
                    KnowledgeNodeModel.user_id == user_id,
                    KnowledgeNodeModel.type == KnowledgeType.PROJECT.value,
                    (KnowledgeNodeModel.id == decision_in.project_id)
                    | (KnowledgeNodeModel.source_id == decision_in.project_id),
                )
            )
            proj_node = (await session.execute(proj_stmt)).scalar_one_or_none()
            if proj_node:
                edge = KnowledgeEdgeModel(
                    user_id=user_id,
                    source_node_id=node.id,
                    target_node_id=proj_node.id,
                    relation_type=KnowledgeRelationType.BELONGS_TO.value,
                    confidence=1.0,
                    source="DECISION_TRACKER",
                )
                session.add(edge)

        await AuditLogger.log_event(
            db_session=session,
            user_id=user_id,
            event_type="knowledge.decision_recorded",
            decision="ALLOWED",
            success=True,
            metadata={"decision": decision_in.decision, "project_id": decision_in.project_id},
        )

        await session.commit()
        await self.search_engine.invalidate_cache(user_id)

        return DecisionResponse(
            id=node.id,
            decision=node.title,
            rationale=node.content,
            project_id=node.project_id,
            status=DecisionStatus.ACTIVE,
            source=decision_in.source,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )

    async def supersede_decision(
        self,
        session: AsyncSession,
        user_id: str,
        old_decision_node_id: str,
        new_decision_text: str,
        rationale: str | None = None,
        reason: str | None = None,
    ) -> DecisionResponse:
        """Supersede an existing decision with a new decision and connect via SUPERSEDES edge."""
        # 1. Fetch old decision node
        stmt = select(KnowledgeNodeModel).where(
            and_(
                KnowledgeNodeModel.id == old_decision_node_id,
                KnowledgeNodeModel.user_id == user_id,
                KnowledgeNodeModel.type == KnowledgeType.DECISION.value,
            )
        )
        old_node = (await session.execute(stmt)).scalar_one_or_none()
        if not old_node:
            raise ValueError(f"Decision '{old_decision_node_id}' not found or access denied.")

        # 2. Mark old decision as SUPERSEDED
        old_node.status = DecisionStatus.SUPERSEDED.value
        old_node.updated_at = datetime.now(UTC)

        # 3. Create new decision
        new_decision_in = DecisionCreate(
            decision=new_decision_text,
            rationale=rationale or f"Supersedes prior decision: {old_node.title}",
            project_id=old_node.project_id,
            source="USER_EXPLICIT",
        )
        new_resp = await self.record_decision(session, user_id, new_decision_in)

        # 4. Link with SUPERSEDES edge: new_node -> SUPERSEDES -> old_node
        edge = KnowledgeEdgeModel(
            user_id=user_id,
            source_node_id=new_resp.id,
            target_node_id=old_node.id,
            relation_type=KnowledgeRelationType.SUPERSEDES.value,
            confidence=1.0,
            source="DECISION_SUPERSEDED",
        )
        session.add(edge)
        await AuditLogger.log_event(
            db_session=session,
            user_id=user_id,
            event_type="knowledge.decision_superseded",
            decision="ALLOWED",
            success=True,
            metadata={
                "old_decision_id": old_node.id,
                "new_decision": new_decision_text,
                "reason": reason,
            },
        )

        await session.commit()
        await self.search_engine.invalidate_cache(user_id)

        return DecisionResponse(
            id=new_resp.id,
            decision=new_resp.decision,
            rationale=new_resp.rationale,
            project_id=new_resp.project_id,
            status=DecisionStatus.ACTIVE,
            source="USER_EXPLICIT",
            created_at=new_resp.created_at,
            updated_at=new_resp.updated_at,
            superseded_by=None,
        )

    async def list_decisions(
        self, session: AsyncSession, user_id: str, project_id: str | None = None
    ) -> list[DecisionResponse]:
        """List active and superseded decisions."""
        filters = [
            KnowledgeNodeModel.user_id == user_id,
            KnowledgeNodeModel.type == KnowledgeType.DECISION.value,
            KnowledgeNodeModel.status != "DELETED",
        ]
        if project_id:
            filters.append(KnowledgeNodeModel.project_id == project_id)

        stmt = select(KnowledgeNodeModel).where(and_(*filters)).order_by(KnowledgeNodeModel.created_at.desc())
        res = await session.execute(stmt)
        nodes = list(res.scalars().all())

        return [
            DecisionResponse(
                id=n.id,
                decision=n.title,
                rationale=n.content,
                project_id=n.project_id,
                status=DecisionStatus(n.status)
                if n.status in DecisionStatus._value2member_map_
                else DecisionStatus.ACTIVE,
                source=n.node_metadata.get("source", "USER_EXPLICIT") if n.node_metadata else "USER_EXPLICIT",
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in nodes
        ]

    # --- Search & Traversal Delegation ---

    async def search(
        self, session: AsyncSession, user_id: str, request: KnowledgeSearchRequest
    ) -> list[KnowledgeSearchResultItem]:
        """Delegate search to HybridSearchEngine."""
        return await self.search_engine.search(session, user_id, request)

    async def get_node_sources(
        self, session: AsyncSession, user_id: str, node_id: str
    ) -> list[KnowledgeSourceResponse]:
        """Get provenance sources associated with a node."""
        node_stmt = select(KnowledgeNodeModel).where(
            and_(KnowledgeNodeModel.id == node_id, KnowledgeNodeModel.user_id == user_id)
        )
        node = (await session.execute(node_stmt)).scalar_one_or_none()
        if not node:
            return []

        src_stmt = select(KnowledgeSourceModel).where(
            and_(
                KnowledgeSourceModel.user_id == user_id,
                KnowledgeSourceModel.source_id == node.source_id,
            )
        )
        sources = (await session.execute(src_stmt)).scalars().all()
        return [KnowledgeSourceResponse.model_validate(s) for s in sources]
