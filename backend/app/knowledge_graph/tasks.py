"""Task memory modeling, state history, and continuity queries (INVARIANTS 50, 51, 158)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid


class TaskMemoryManager:
    """Tracks task state history and answers 'What was left from yesterday?' without fabricating tasks."""

    def __init__(self) -> None:
        # task_id -> dict
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def record_task(
        self,
        title: str,
        owner: str,
        status: str = "OPEN",
        deadline: Optional[datetime] = None,
        project_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        t_id = str(uuid.uuid4())
        record = {
            "task_id": t_id,
            "title": title.strip(),
            "owner": owner,
            "status": status,
            "deadline": deadline.isoformat() if deadline else None,
            "project_id": project_id,
            "dependencies": dependencies or [],
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._tasks[t_id] = record
        return record

    def get_task_continuity(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """INVARIANT 158: Answers 'What was left from yesterday?' by retrieving open tasks."""
        return [
            t for t in self._tasks.values()
            if t["status"] in ("OPEN", "IN_PROGRESS", "BLOCKED")
            and (project_id is None or t["project_id"] == project_id)
        ]
