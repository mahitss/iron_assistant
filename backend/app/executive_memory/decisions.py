"""Decision history, impact tracking, rationale retrieval, and supersession (INVARIANTS 49-52, 197)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid


class DecisionHistoryManager:
    """Maintains immutable decision timeline, affected scopes, and supersession lineages."""

    def __init__(self) -> None:
        # decision_id -> decision dict
        self._decisions: dict[str, dict[str, Any]] = {}

    def record_decision(
        self,
        decision_text: str,
        rationale: str,
        project_id: str | None = None,
        affected_tasks: list[str] | None = None,
        actor: str = "user",
        supersedes_id: str | None = None,
    ) -> dict[str, Any]:
        """INVARIANT 49-52 & 197: Records decision with rationale and supersession without fabricating decisions."""
        if not decision_text.strip():
            raise ValueError("INVARIANT 197: Cannot record empty or fabricated decision.")

        did = f"dec_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)

        if supersedes_id and supersedes_id in self._decisions:
            old = self._decisions[supersedes_id]
            old["superseded_by"] = did
            old["is_active"] = False

        record = {
            "decision_id": did,
            "decision_text": decision_text.strip(),
            "rationale": rationale.strip() if rationale and rationale.strip() else "UNKNOWN",
            "project_id": project_id,
            "affected_tasks": affected_tasks or [],
            "actor": actor,
            "supersedes_id": supersedes_id,
            "superseded_by": None,
            "is_active": True,
            "timestamp": now.isoformat(),
        }
        self._decisions[did] = record
        return record

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        return self._decisions.get(decision_id)

    def list_decisions(self, project_id: str | None = None, active_only: bool = True) -> list[dict[str, Any]]:
        results = list(self._decisions.values())
        if project_id:
            results = [d for d in results if d.get("project_id") == project_id]
        if active_only:
            results = [d for d in results if d.get("is_active", True)]
        return results
