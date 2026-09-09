"""Temporal context reasoning, timeline synthesis, evidence-based causality, and conflict detection."""

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.models import KnowledgeNodeModel, KnowledgeSourceModel
from app.knowledge.schemas import (
    KnowledgeTimelineItem,
    KnowledgeTimelineResponse,
    KnowledgeType,
)

logger = logging.getLogger("kairo.knowledge.temporal")


class TemporalReasoner:
    """Provides chronological timeline synthesis, causal verification, and conflict detection."""

    async def get_timeline(
        self,
        session: AsyncSession,
        user_id: str,
        project_id: str | None = None,
        type_filter: KnowledgeType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
    ) -> KnowledgeTimelineResponse:
        """Fetch chronologically ordered timeline events for a project or user workspace."""
        filters = [
            KnowledgeNodeModel.user_id == user_id,
            KnowledgeNodeModel.status != "DELETED",
        ]
        if project_id:
            filters.append(KnowledgeNodeModel.project_id == project_id)
        if type_filter:
            filters.append(KnowledgeNodeModel.type == type_filter.value)
        if date_from:
            filters.append(KnowledgeNodeModel.created_at >= date_from)
        if date_to:
            filters.append(KnowledgeNodeModel.created_at <= date_to)

        stmt = (
            select(KnowledgeNodeModel)
            .where(and_(*filters))
            .order_by(KnowledgeNodeModel.created_at.desc())
            .limit(limit)
        )
        res = await session.execute(stmt)
        nodes = list(res.scalars().all())

        # Extract sources in batch
        source_ids = [n.source_id for n in nodes if n.source_id]
        src_map: dict[str, str] = {}
        if source_ids:
            src_stmt = select(KnowledgeSourceModel).where(
                and_(
                    KnowledgeSourceModel.user_id == user_id,
                    KnowledgeSourceModel.source_id.in_(source_ids),
                )
            )
            src_res = await session.execute(src_stmt)
            for s in src_res.scalars().all():
                src_map[s.source_id] = s.source_type

        timeline_items = [
            KnowledgeTimelineItem(
                node_id=n.id,
                timestamp=n.created_at,
                title=n.title,
                summary=n.summary,
                type=n.type,
                source_id=n.source_id,
                source_type=src_map.get(n.source_id, "SYSTEM_DERIVED"),
                project_id=n.project_id,
                status=n.status,
            )
            for n in nodes
        ]

        return KnowledgeTimelineResponse(
            project_id=project_id,
            total_events=len(timeline_items),
            events=timeline_items,
        )

    def verify_causality_evidence(
        self,
        cause_node: KnowledgeNodeModel,
        effect_node: KnowledgeNodeModel,
    ) -> tuple[bool, float, str]:
        """Verify empirical evidence for a CAUSED relationship.

        Strictly prevents inferring causality from mere temporal coincidence.
        Returns: (has_evidence: bool, confidence: float, explanation: str)
        """
        # Temporal ordering prerequisite: cause must happen before or at the same time as effect
        cause_time = (
            cause_node.created_at.replace(tzinfo=UTC)
            if cause_node.created_at.tzinfo is None
            else cause_node.created_at
        )
        effect_time = (
            effect_node.created_at.replace(tzinfo=UTC)
            if effect_node.created_at.tzinfo is None
            else effect_node.created_at
        )
        if cause_time > effect_time:
            return False, 0.0, "Cause timestamp cannot occur after effect timestamp."

        effect_text = f"{effect_node.title} {effect_node.summary} {effect_node.content or ''}".lower()

        # 1. Commit SHA explicitly referenced in CI / Workflow failure
        if cause_node.type == KnowledgeType.COMMIT.value and effect_node.type in (
            KnowledgeType.WORKFLOW_RUN.value,
            KnowledgeType.NOTIFICATION.value,
        ):
            commit_id = cause_node.source_id.lower()
            clean_sha = re.sub(r"^commit[_\-\/:\s]?", "", commit_id).strip()
            shas_to_check = [s for s in [commit_id, clean_sha, clean_sha[:7]] if len(s) >= 4]
            if any(sha in effect_text for sha in shas_to_check):
                matched = clean_sha or commit_id
                return True, 0.95, f"Commit {matched[:7]} is explicitly cited in the execution output."

        # 2. Workflow failure explicitly cited in notification or task
        if cause_node.type == KnowledgeType.WORKFLOW_RUN.value and effect_node.type in (
            KnowledgeType.NOTIFICATION.value,
            KnowledgeType.TASK.value,
        ):
            if cause_node.source_id.lower() in effect_text or cause_node.title.lower() in effect_text:
                return True, 0.90, f"Workflow run {cause_node.source_id} is referenced in event details."

        # 3. Direct explicit reference in metadata
        effect_meta = effect_node.node_metadata or {}
        if effect_meta.get("caused_by_source_id") == cause_node.source_id:
            return True, 0.95, "Explicit causal reference in authoritative event metadata."

        return False, 0.0, "No empirical causal evidence found connecting events beyond temporal proximity."

    async def detect_conflicts(
        self,
        session: AsyncSession,
        user_id: str,
        project_id: str | None = None,
        candidate_title: str | None = None,
    ) -> list[dict[str, Any]]:
        """Identify contradictory statements across knowledge nodes for a user or project.

        Surfaces conflicts explicitly (e.g. Python version mismatch) rather than hallucinating resolution.
        """
        filters = [
            KnowledgeNodeModel.user_id == user_id,
            KnowledgeNodeModel.status == "ACTIVE",
        ]
        if project_id:
            filters.append(KnowledgeNodeModel.project_id == project_id)

        stmt = select(KnowledgeNodeModel).where(and_(*filters)).limit(100)
        res = await session.execute(stmt)
        nodes = list(res.scalars().all())

        conflicts: list[dict[str, Any]] = []

        # Version conflict heuristics: extract patterns like "python 3.x", "postgres 16", etc.
        version_pattern = re.compile(
            r"\b([a-zA-Z0-9_\-\.]+)\s+(?:version\s+|v)?(\d+\.\d+(?:\.\d+)?)\b", re.IGNORECASE
        )

        claims: dict[str, list[tuple[str, str, KnowledgeNodeModel]]] = {}
        for n in nodes:
            text = f"{n.title} {n.summary}"
            matches = version_pattern.findall(text)
            for entity, ver in matches:
                key = entity.lower()
                if key not in claims:
                    claims[key] = []
                claims[key].append((ver, n.id, n))

        # Check for multiple differing versions for the same entity
        for entity, entries in claims.items():
            versions = {v for v, _, _ in entries}
            if len(versions) > 1:
                conflicting_nodes = [
                    {
                        "node_id": node.id,
                        "title": node.title,
                        "type": node.type,
                        "claimed_version": ver,
                        "timestamp": node.created_at.isoformat(),
                        "source_id": node.source_id,
                    }
                    for ver, _, node in entries
                ]
                conflicts.append(
                    {
                        "entity": entity,
                        "differing_values": list(versions),
                        "conflict_reason": f"Conflicting versions reported for '{entity}': {', '.join(versions)}",
                        "sources": conflicting_nodes,
                    }
                )

        return conflicts
