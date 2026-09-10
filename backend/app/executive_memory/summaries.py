"""Executive project briefing and traceable summary synthesis (INVARIANTS 22-26, 147-150)."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from typing import Any
import uuid

from app.executive_memory.schemas import ExecutiveBriefSchema


class ExecutiveSummaryManager:
    """Generates structured, compact, and traceable project briefings with staleness invalidation."""

    def __init__(self) -> None:
        # summary_id -> ExecutiveBriefSchema
        self._summaries: dict[str, ExecutiveBriefSchema] = {}
        # project_id -> latest summary_id
        self._latest_by_project: dict[str, str] = {}

    def _compute_hash(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def generate_brief(
        self,
        project_id: str,
        current_status: str,
        recent_progress: list[dict[str, Any]] | None = None,
        open_work: list[dict[str, Any]] | None = None,
        blockers: list[dict[str, Any]] | None = None,
        decisions: list[dict[str, Any]] | None = None,
        risks: list[dict[str, Any]] | None = None,
        next_actions: list[dict[str, Any]] | None = None,
    ) -> ExecutiveBriefSchema:
        """INVARIANT 22 & 148: Generates brief containing CURRENT, RECENT, OPEN, BLOCKED, NEXT, RISKS, DECISIONS."""
        payload = {
            "current_status": current_status,
            "recent_progress": recent_progress or [],
            "open_work": open_work or [],
            "blockers": blockers or [],
            "decisions": decisions or [],
            "risks": risks or [],
            "next_actions": next_actions or [],
        }
        staleness_hash = self._compute_hash(payload)

        sid = f"brf_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        brief = ExecutiveBriefSchema(
            summary_id=sid,
            project_id=project_id,
            current_status=current_status,
            recent_progress=recent_progress or [],
            open_work=open_work or [],
            blockers=blockers or [],
            decisions=decisions or [],
            risks=risks or [],
            next_actions=next_actions or [],
            as_of=now,
            staleness_hash=staleness_hash,
            created_at=now,
        )
        self._summaries[sid] = brief
        self._latest_by_project[project_id] = sid
        return brief

    def get_latest_brief(self, project_id: str) -> ExecutiveBriefSchema | None:
        sid = self._latest_by_project.get(project_id)
        return self._summaries.get(sid) if sid else None

    def is_brief_stale(self, project_id: str, current_state_payload: dict[str, Any]) -> bool:
        """INVARIANT 24 & 127: Checks whether existing summary hash diverges from current state."""
        brief = self.get_latest_brief(project_id)
        if not brief:
            return True
        current_hash = self._compute_hash(current_state_payload)
        return brief.staleness_hash != current_hash

    def invalidate_summary(self, project_id: str, reason: str = "") -> None:
        """INVARIANT 24 & 127: Invalidates cached executive summary for a project."""
        if project_id in self._latest_by_project:
            del self._latest_by_project[project_id]
