"""Evidence-backed blocker tracking and causal verification (INVARIANTS 38-41, 92-93, 199)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.executive_memory.safety import ExecutiveSafetyGuard
from app.executive_memory.schemas import BlockerSchema, BlockerStatus


class BlockerManager:
    """Tracks active and resolved blockers grounded strictly in empirical evidence."""

    def __init__(self) -> None:
        # blocker_id -> BlockerSchema
        self._blockers: dict[str, BlockerSchema] = {}

    def report_blocker(
        self,
        description: str,
        affected_tasks: list[str],
        source: str = "ENVIRONMENT",
        severity: str = "HIGH",
        owner: str = "team",
        causality_evidence: dict[str, Any] | str | None = None,
        project_id: str | None = None,
    ) -> BlockerSchema:
        """INVARIANT 40 & 41: Records blocker. Validates causality evidence without fabricating reasons."""
        return self.create_blocker(
            description=description,
            affected_tasks=affected_tasks,
            source=source,
            severity=severity,
            owner=owner,
            causality_evidence=causality_evidence,
            project_id=project_id,
        )

    def create_blocker(
        self,
        description: str,
        affected_tasks: list[str],
        source: str = "ENVIRONMENT",
        severity: str = "HIGH",
        owner: str | None = None,
        causality_evidence: str | dict[str, Any] | None = None,
        project_id: str | None = None,
    ) -> BlockerSchema:
        """INVARIANT 40 & 41: Records blocker with mandatory empirical causality evidence."""
        ExecutiveSafetyGuard.validate_blocker_causality(description, causality_evidence)
        bid = f"blk_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        blocker = BlockerSchema(
            blocker_id=bid,
            description=description.strip(),
            affected_tasks=affected_tasks,
            source=source,
            severity=severity,
            owner=owner or "team",
            detected_at=now,
            status=BlockerStatus.ACTIVE,
            causality_evidence=causality_evidence or {},
            project_id=project_id,
        )
        self._blockers[bid] = blocker
        return blocker

    def resolve_blocker(
        self,
        blocker_id: str,
        resolution_evidence: str | None = None,
        resolution_notes: str | None = None,
    ) -> BlockerSchema:
        """Marks blocker as resolved."""
        b = self._blockers.get(blocker_id)
        if not b:
            raise KeyError(f"Blocker '{blocker_id}' not found.")
        b.status = BlockerStatus.RESOLVED
        b.resolved_at = datetime.now(UTC)
        res_text = resolution_evidence or resolution_notes
        if res_text:
            if isinstance(b.causality_evidence, dict):
                b.causality_evidence["resolution_notes"] = res_text
            else:
                b.causality_evidence = f"{b.causality_evidence} | Resolved: {res_text}"
        return b

    def list_blockers(
        self,
        project_id: str | None = None,
        active_only: bool = True,
    ) -> list[BlockerSchema]:
        """INVARIANT 92 & 93: Returns active evidence-backed blockers."""
        results = list(self._blockers.values())
        if project_id:
            results = [b for b in results if b.project_id == project_id]
        if active_only:
            results = [b for b in results if b.status == BlockerStatus.ACTIVE]
        return results
