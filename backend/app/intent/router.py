"""REST API endpoints for Kairo Unified Command, Intent, and Control Layer (Task 35, Spec 122, 123)."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.intent.commands import CommandService
from app.intent.parser import IntentParser
from app.intent.planner_bridge import CommandRouter
from app.intent.schemas import (
    CommandCreateRequest,
    CommandResolveRequest,
    CommandResponse,
    IntentSchema,
)

logger = logging.getLogger("kairo.intent.router")

router = APIRouter(prefix="/commands", tags=["commands"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header, defaulting to 'default_user'."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


@router.post("", response_model=CommandResponse, status_code=status.HTTP_200_OK)
async def submit_command(
    request: CommandCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> CommandResponse:
    """
    Submits a natural-language command, extracts structured intent, resolves references,
    persists records, and delegates execution or clarification.
    """
    try:
        cmd_schema, intent_schema = IntentParser.parse_command(
            raw_text=request.text,
            user_id=user_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            attachments=request.attachments,
            source_interface=request.source_interface,
            project_hint=request.project_hint,
            clarification_response=request.clarification_response,
        )

        # Persist command and intent
        await CommandService.record_command_and_intent(
            db_session=db_session,
            command_schema=cmd_schema,
            intent_schema=intent_schema,
        )

        # Route to domain subsystems if unambiguous and valid
        exec_summary = await CommandRouter.route_intent(
            intent=intent_schema,
            user_id=user_id,
            db_session=db_session,
        )

        return CommandResponse(
            command_id=cmd_schema.command_id,
            intent=intent_schema,
            ambiguity=intent_schema.ambiguity,
            execution_summary=exec_summary,
        )
    except Exception as exc:
        logger.error("Error processing command: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command processing error: {str(exc)}",
        )


@router.post("/resolve", response_model=CommandResponse, status_code=status.HTTP_200_OK)
async def resolve_command(
    request: CommandResolveRequest,
    user_id: str = Depends(get_current_user_id),
) -> CommandResponse:
    """
    Spec 123: Resolve-only endpoint that analyzes intent and references without executing.
    Returns: intent, resolved references, ambiguity, risk, next action.
    """
    try:
        cmd_schema, intent_schema = IntentParser.parse_command(
            raw_text=request.text,
            user_id=user_id,
            session_id=request.session_id,
            conversation_id=request.conversation_id,
            attachments=request.attachments,
            source_interface=request.source_interface,
            project_hint=request.project_hint,
        )

        return CommandResponse(
            command_id=cmd_schema.command_id,
            intent=intent_schema,
            ambiguity=intent_schema.ambiguity,
            execution_summary={"status": "RESOLVED_ONLY", "executed": False},
        )
    except Exception as exc:
        logger.error("Error resolving command: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Command resolution error: {str(exc)}",
        )


@router.get("/{command_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
async def get_command(
    command_id: str,
    user_id: str = Depends(get_current_user_id),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve details of a previously submitted command, enforcing user tenant isolation."""
    cmd = await CommandService.get_command(
        db_session=db_session,
        command_id=command_id,
        user_id=user_id,
    )
    if not cmd:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Command '{command_id}' not found.",
        )

    intents_data = []
    for i in cmd.intents:
        intents_data.append({
            "id": i.id,
            "type": i.type,
            "objective": i.objective,
            "risk": i.risk,
            "status": i.status,
            "confidence": i.confidence,
            "target": i.target_json,
            "ambiguity": i.ambiguity_json,
            "created_at": i.created_at.isoformat(),
        })

    return {
        "command_id": cmd.id,
        "user_id": cmd.user_id,
        "session_id": cmd.session_id,
        "conversation_id": cmd.conversation_id,
        "text": cmd.text,
        "original_text": cmd.original_text,
        "source_interface": cmd.source_interface,
        "project_hint": cmd.project_hint,
        "attachments": cmd.attachments_json,
        "created_at": cmd.created_at.isoformat(),
        "intents": intents_data,
    }
