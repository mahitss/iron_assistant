"""Next action generation, user intent supremacy, and authorization checks (INVARIANTS 74-78, 200, 212-214)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.executive_memory.safety import ExecutiveSafetyGuard
from app.executive_memory.schemas import NextActionSchema, NextActionStatus, OpenLoopSchema


class NextActionEngine:
    """Derives actionable next steps from open loops without falsely claiming existing execution plans."""

    def __init__(self, open_loop_mgr: Any = None) -> None:
        self.open_loop_mgr = open_loop_mgr
        # action_id -> NextActionSchema
        self._actions: dict[str, NextActionSchema] = {}

    def generate_from_open_loops(
        self,
        project_id: str | None = None,
        explicit_user_intent: str | None = None,
    ) -> list[NextActionSchema]:
        """INVARIANT 75, 212, 214: Generates next actions from open loops with explicit user intent supremacy."""
        loops = []
        if self.open_loop_mgr:
            loops = self.open_loop_mgr.list_open_loops(project_id=project_id)

        actions = []
        if explicit_user_intent:
            aid = f"act_{uuid.uuid4().hex[:12]}"
            action = NextActionSchema(
                action_id=aid,
                objective=explicit_user_intent.strip(),
                rationale="Explicit user intent override takes absolute supremacy (INVARIANT 214)",
                dependencies=[],
                authorization_status="REQUIRED",
                confidence=1.0,
                status=NextActionStatus.RECOMMENDED,
                project_id=project_id,
                created_at=datetime.now(UTC),
            )
            self._actions[aid] = action
            actions.append(action)
            return actions

        for loop in loops[:3]:  # top 3 loops
            act = self.generate_next_action(
                open_loop=loop,
                rationale=f"Derived from open loop {loop.loop_id}",
            )
            actions.append(act)
        return actions

    def generate_next_action(
        self,
        open_loop: OpenLoopSchema,
        rationale: str,
        dependencies: list[str] | None = None,
        confidence: float = 0.8,
        explicit_user_intent: str | None = None,
    ) -> NextActionSchema:
        """INVARIANT 74, 75, 200, 214: Generates next action.
        User explicit intent overrides inferred objectives.
        """
        aid = f"act_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)

        # INVARIANT 214: Current explicit user intent overrides inferred next objective
        objective = explicit_user_intent.strip() if explicit_user_intent else f"Resolve: {open_loop.description}"
        action_rationale = rationale.strip() if rationale and rationale.strip() else "Derived from active open loop"

        action = NextActionSchema(
            action_id=aid,
            objective=objective,
            rationale=action_rationale,
            dependencies=dependencies or open_loop.dependencies,
            authorization_status="REQUIRED",  # INVARIANT 76: Recommendations are not authorization
            confidence=confidence,
            status=NextActionStatus.RECOMMENDED,
            project_id=open_loop.scope_id,
            created_at=now,
        )
        self._actions[aid] = action
        return action

    def authorize_and_execute_action(
        self,
        action_id: str,
        authorization_token: Any,
    ) -> NextActionSchema:
        """INVARIANT 76 & 77: Requires valid authorization token to move to EXECUTED."""
        act = self._actions.get(action_id)
        if not act:
            raise ValueError(f"Action '{action_id}' not found.")

        ExecutiveSafetyGuard.assert_no_action_authorization(act.objective, authorization_token)
        act.authorization_status = "GRANTED"
        act.status = NextActionStatus.EXECUTED
        return act

    def list_next_actions(self, project_id: str | None = None) -> list[NextActionSchema]:
        results = list(self._actions.values())
        if project_id:
            results = [a for a in results if a.project_id == project_id]
        return results
