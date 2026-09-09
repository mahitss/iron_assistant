"""Command persistence, history tracking, and clarification continuity (Spec 48, 71, 72, 134, 136)."""

from datetime import UTC, datetime
import logging
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.intent.models import CommandModel, IntentModel
from app.intent.schemas import (
    CommandSchema,
    IntentSchema,
)

logger = logging.getLogger("kairo.intent.commands")


class CommandService:
    """Manages the persistence, retrieval, and continuity of commands and structured intents."""

    @classmethod
    async def record_command_and_intent(
        cls,
        db_session: AsyncSession,
        command_schema: CommandSchema,
        intent_schema: IntentSchema,
    ) -> tuple[CommandModel, IntentModel]:
        """Persists the normalized command and its extracted structured intent."""
        now = datetime.now(UTC)

        cmd_model = CommandModel(
            id=command_schema.command_id,
            user_id=command_schema.user_id,
            session_id=command_schema.session_id,
            conversation_id=command_schema.conversation_id,
            text=command_schema.text,
            original_text=command_schema.original_text,
            attachments_json=[a.model_dump() for a in command_schema.attachments],
            source_interface=command_schema.source_interface,
            project_hint=command_schema.project_hint,
            created_at=command_schema.created_at or now,
        )
        db_session.add(cmd_model)

        intent_model = IntentModel(
            id=intent_schema.intent_id,
            command_id=command_schema.command_id,
            user_id=command_schema.user_id,
            type=intent_schema.type.value,
            objective=intent_schema.objective,
            entities_json=[e.model_dump() for e in intent_schema.entities],
            references_json=intent_schema.references,
            target_json=intent_schema.target.model_dump() if intent_schema.target else None,
            constraints_json=intent_schema.constraints.model_dump(),
            requested_action=intent_schema.requested_action,
            confidence=intent_schema.confidence,
            ambiguity_json=intent_schema.ambiguity.model_dump(),
            risk=intent_schema.risk.value,
            status=intent_schema.status,
            next_action=intent_schema.next_action,
            created_at=intent_schema.created_at or now,
        )
        db_session.add(intent_model)

        await db_session.commit()
        await db_session.refresh(cmd_model)
        await db_session.refresh(intent_model)

        return cmd_model, intent_model

    @classmethod
    async def get_command(
        cls,
        db_session: AsyncSession,
        command_id: str,
        user_id: str,
    ) -> CommandModel | None:
        """Retrieves a specific command enforcing user tenant isolation."""
        stmt = (
            select(CommandModel)
            .where(CommandModel.id == command_id, CommandModel.user_id == user_id)
        )
        res = await db_session.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def list_recent_commands(
        cls,
        db_session: AsyncSession,
        user_id: str,
        limit: int = 10,
    ) -> list[CommandModel]:
        """Retrieves bounded recent commands for context and reference resolution."""
        stmt = (
            select(CommandModel)
            .where(CommandModel.user_id == user_id)
            .order_by(desc(CommandModel.created_at))
            .limit(limit)
        )
        res = await db_session.execute(stmt)
        return list(res.scalars().all())
