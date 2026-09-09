"""Durable Database Persistence Adapter, Immutability Guards, and Journaling (Task 45)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.autonomy.models import (
    AutonomousCheckpointModel,
    AutonomousCompletionRecordModel,
    AutonomousGoalModel,
    AutonomousJournalEntryModel,
    AutonomousRunModel,
)

logger = logging.getLogger("kairo.autonomy.persistence")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JournalTamperingError(Exception):
    """Raised when an operation attempts to modify or delete historical journal records (Spec 130)."""


class AutonomyPersistenceManager:
    """Async database persistence manager integrating SQLAlchemy models for durable recovery (Spec 7-12, 107, 129-130)."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session
        # In-memory journal store for tests and fallback
        self._in_memory_journals: Dict[str, List[Dict[str, Any]]] = {}

    async def save_goal(
        self,
        goal_id: str,
        title: str,
        description: str,
        user_id: str,
        project_id: str,
        success_criteria: List[str],
        hard_constraints: List[str],
        scope_data: Dict[str, Any],
    ) -> AutonomousGoalModel:
        """Persist authorized goal in database (Spec 7)."""
        model = AutonomousGoalModel(
            id=goal_id,
            title=title,
            description=description,
            user_id=user_id,
            project_id=project_id,
            status="ACTIVE",
            success_criteria=success_criteria,
            hard_constraints=hard_constraints,
            scope_data=scope_data,
        )
        if self.session:
            self.session.add(model)
            await self.session.commit()
            await self.session.refresh(model)
        return model

    async def save_run(
        self,
        run_id: str,
        goal_id: str,
        plan_id: str,
        plan_version: int,
        status: str,
        autonomy_level: str,
        owner_user_id: str,
        project_id: str,
        budget_data: Dict[str, Any],
        deadline_at: Optional[datetime] = None,
    ) -> AutonomousRunModel:
        """Persist autonomous run state machine in database (Spec 2, 8)."""
        model = AutonomousRunModel(
            id=run_id,
            goal_id=goal_id,
            plan_id=plan_id,
            plan_version=plan_version,
            status=status,
            autonomy_level=autonomy_level,
            owner_user_id=owner_user_id,
            project_id=project_id,
            budget_data=budget_data,
            deadline_at=deadline_at,
        )
        if self.session:
            self.session.add(model)
            await self.session.commit()
            await self.session.refresh(model)
        return model

    async def append_journal_entry(
        self,
        run_id: str,
        event_type: str,
        payload: Dict[str, Any],
        step_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Append immutable execution journal record. Modifying existing entries is strictly forbidden (Spec 129, 130)."""
        run_journal = self._in_memory_journals.setdefault(run_id, [])
        seq = len(run_journal) + 1
        entry_id = f"jrn_{uuid.uuid4().hex[:12]}"

        record = {
            "id": entry_id,
            "run_id": run_id,
            "event_type": event_type,
            "step_id": step_id,
            "payload": payload,
            "sequence_num": seq,
            "created_at": utc_now().isoformat(),
        }
        run_journal.append(record)

        if self.session:
            model = AutonomousJournalEntryModel(
                id=entry_id,
                run_id=run_id,
                event_type=event_type,
                step_id=step_id,
                payload=payload,
                sequence_num=seq,
            )
            self.session.add(model)
            await self.session.commit()

        logger.info("Journal entry #%d appended to run %s: %s", seq, run_id, event_type)
        return record

    def get_run_journal(self, run_id: str) -> List[Dict[str, Any]]:
        return list(self._in_memory_journals.get(run_id, []))

    def assert_journal_immutability(self, run_id: str, proposed_history: List[Dict[str, Any]]) -> None:
        """Verify that historical journal has not been truncated or mutated (Spec 130)."""
        current = self._in_memory_journals.get(run_id, [])
        if len(proposed_history) < len(current):
            raise JournalTamperingError("Journal records cannot be truncated or deleted.")
        for curr, prop in zip(current, proposed_history):
            if curr["id"] != prop.get("id") or curr["event_type"] != prop.get("event_type") or curr["payload"] != prop.get("payload"):
                raise JournalTamperingError(f"Historical journal entry {curr['id']} was modified!")
