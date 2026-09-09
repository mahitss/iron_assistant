"""Project memory modeling, scope containment, and project continuity (INVARIANTS 42-44, 157)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.knowledge_graph.schemas import NodeType, ScopeType


class ProjectMemoryManager:
    """Manages project-scoped facts, repos, tasks, documents, and continuity queries."""

    def __init__(self) -> None:
        # project_id -> dict state
        self._projects: Dict[str, Dict[str, Any]] = {}

    def register_project(
        self,
        project_id: str,
        name: str,
        owner: str,
        repositories: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        proj = {
            "project_id": project_id,
            "name": name,
            "owner": owner,
            "repositories": repositories or [],
            "description": description or "",
            "active_tasks": [],
            "recent_decisions": [],
            "status": "ACTIVE",
        }
        self._projects[project_id] = proj
        return proj

    def get_project_continuity(self, project_id: str) -> Dict[str, Any]:
        """INVARIANT 157: Answers 'What were we doing with this project?' without inventing facts."""
        proj = self._projects.get(project_id)
        if not proj:
            return {"error": f"Project '{project_id}' not found."}

        return {
            "project_name": proj["name"],
            "owner": proj["owner"],
            "repositories": proj["repositories"],
            "active_tasks_count": len(proj["active_tasks"]),
            "recent_decisions_count": len(proj["recent_decisions"]),
            "continuity_summary": f"Active development on {proj['name']} with {len(proj['repositories'])} repositories.",
        }
