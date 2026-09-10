"""Compact context synthesis and packing for the Context Engine (INVARIANTS 104-106)."""

from __future__ import annotations

from typing import Any

from app.executive_memory.schemas import ExecutiveBriefSchema, ExecutiveStateSchema


class ContextSynthesisEngine:
    """Packs compact, high-value executive context for LLM prompt context windows."""

    @classmethod
    def pack_executive_context(
        cls,
        state: ExecutiveStateSchema,
        brief: ExecutiveBriefSchema | None = None,
        max_tokens_budget: int = 1500,
    ) -> dict[str, Any]:
        """INVARIANT 104 & 105: Context packing using current state, recent changes, important history, open loops, and next actions."""
        packed = {
            "scope": state.scope,
            "project_id": state.scope_id,
            "timestamp": state.timestamp.isoformat(),
            "active_projects_count": len(state.active_projects),
            "open_loops": [l.model_dump() for l in state.open_loops[:5]],
            "active_blockers": [b.model_dump() for b in state.blockers[:3]],
            "recent_decisions": state.recent_decisions[:3],
            "next_actions": [a.model_dump() for a in state.next_actions[:3]],
        }

        if brief:
            packed["current_brief"] = brief.current_status
            packed["recent_progress"] = brief.recent_progress[:3]

        return packed
