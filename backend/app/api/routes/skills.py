"""REST API endpoints for Kairo Skills and Capability System."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.security.center import get_security_center
from app.skills.catalog import populate_default_skills
from app.skills.executor import SkillExecutor
from app.skills.registry import SkillRegistry
from app.skills.schemas import (
    SkillCategory,
    SkillDetailResponse,
    SkillExecuteRequest,
    SkillExecutionRecord,
    SkillHealthStatus,
    SkillResult,
    SkillSummaryItem,
    SkillToggleRequest,
)
from app.tools.executor import ToolExecutor
from app.tools.registry import create_default_tool_registry

logger = logging.getLogger("kairo.api.skills")

router = APIRouter(prefix="/skills", tags=["Skills"])

# Application-wide singleton instances
_TOOL_REGISTRY = create_default_tool_registry()
_SKILL_REGISTRY = SkillRegistry(tool_registry=_TOOL_REGISTRY)
populate_default_skills(_SKILL_REGISTRY)

_TOOL_EXECUTOR = ToolExecutor(registry=_TOOL_REGISTRY)
_SKILL_EXECUTOR = SkillExecutor(
    registry=_SKILL_REGISTRY,
    tool_executor=_TOOL_EXECUTOR,
    security_center=get_security_center(),
)


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_skill_registry() -> SkillRegistry:
    """Dependency provider for SkillRegistry."""
    return _SKILL_REGISTRY


def get_skill_executor() -> SkillExecutor:
    """Dependency provider for SkillExecutor."""
    return _SKILL_EXECUTOR


@router.get("", response_model=list[SkillSummaryItem], summary="List available skills")
async def list_skills(
    category: SkillCategory | None = None,
    enabled_only: bool = Query(default=False),
    user_id: str = Depends(get_current_user_id),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> list[SkillSummaryItem]:
    """Retrieve all registered skills, filtered by category and user-specific enable status."""
    manifests = registry.list_skills(category=category, enabled_only=enabled_only, user_id=user_id)
    items: list[SkillSummaryItem] = []

    for m in manifests:
        health_status, _ = registry.resolve_health(m.id)
        items.append(
            SkillSummaryItem(
                id=m.id,
                name=m.name,
                description=m.description,
                version=m.version,
                category=m.category,
                risk_level=m.risk_level,
                enabled=m.enabled,
                source=str(m.source),
                health=health_status,
                health_status=health_status,
                capabilities=m.capabilities,
                project_scoped=m.project_scoped,
                device_scoped=m.device_scoped,
            )
        )
    return items


@router.get("/{skill_id}", response_model=SkillDetailResponse, summary="Get skill manifest and details")
async def get_skill_detail(
    skill_id: str,
    user_id: str = Depends(get_current_user_id),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> SkillDetailResponse:
    """Inspect detailed manifest, limits, and operational health for a specific skill."""
    manifest = registry.get(skill_id, user_id=user_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' not found.",
        )

    health_status, reason = registry.resolve_health(skill_id)
    return SkillDetailResponse(
        id=manifest.id,
        name=manifest.name,
        description=manifest.description,
        version=manifest.version,
        category=manifest.category,
        risk_level=manifest.risk_level,
        enabled=manifest.enabled,
        source=str(manifest.source),
        capabilities=manifest.capabilities,
        required_tools=manifest.required_tools,
        optional_tools=manifest.optional_tools,
        required_permissions=manifest.permissions,
        input_schema=manifest.input_schema,
        output_schema=manifest.output_schema,
        execution_limits=manifest.execution_limits,
        health=health_status,
        health_status=health_status,
        health_reason=reason,
        project_scoped=manifest.project_scoped,
        device_scoped=manifest.device_scoped,
        manifest=manifest,
    )


@router.get("/{skill_id}/health", summary="Check operational health of a skill")
async def get_skill_health(
    skill_id: str,
    registry: SkillRegistry = Depends(get_skill_registry),
) -> dict[str, Any]:
    """Check tool dependencies and operational health status for a skill."""
    manifest = registry.get(skill_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' not found.",
        )

    health_status, reason = registry.resolve_health(skill_id)
    return {
        "skill_id": skill_id,
        "status": health_status.value,
        "health_status": health_status.value,
        "ready": health_status == SkillHealthStatus.HEALTHY,
        "reason": reason,
        "required_tools": manifest.required_tools,
        "optional_tools": manifest.optional_tools,
    }


@router.post("/{skill_id}/execute", response_model=SkillResult, summary="Execute a skill")
async def execute_skill(
    skill_id: str,
    payload: SkillExecuteRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    registry: SkillRegistry = Depends(get_skill_registry),
    executor: SkillExecutor = Depends(get_skill_executor),
) -> SkillResult:
    """Execute a skill end-to-end through validation, planning, SecurityCenter authorization, and tools."""
    manifest = registry.get(skill_id, user_id=user_id)
    if not manifest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' not found.",
        )

    if not manifest.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Skill '{skill_id}' is disabled.",
        )

    result = await executor.execute(
        manifest=manifest,
        inputs=payload.inputs,
        user_id=user_id,
        project_id=payload.project_id,
        device_id=payload.device_id,
        session_id=payload.session_id,
        db_session=db,
    )
    return result


@router.get("/executions/{execution_id}", response_model=SkillExecutionRecord, summary="Get execution status")
async def get_execution_status(
    execution_id: str,
    executor: SkillExecutor = Depends(get_skill_executor),
) -> SkillExecutionRecord:
    """Query runtime status and step details of a specific skill execution."""
    record = executor.get_execution(execution_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found.",
        )
    return record


@router.post("/executions/{execution_id}/cancel", summary="Cancel a running skill execution")
async def cancel_execution(
    execution_id: str,
    executor: SkillExecutor = Depends(get_skill_executor),
) -> dict[str, Any]:
    """Signal cooperative cancellation to a running skill execution."""
    success = executor.cancel_execution(execution_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution '{execution_id}' not found.",
        )
    return {"execution_id": execution_id, "status": "CANCELLED"}


@router.post("/{skill_id}/toggle", summary="Enable or disable a skill for the user")
async def toggle_skill(
    skill_id: str,
    payload: SkillToggleRequest,
    user_id: str = Depends(get_current_user_id),
    registry: SkillRegistry = Depends(get_skill_registry),
) -> dict[str, Any]:
    """Enable or disable a skill for the calling user."""
    success = registry.toggle_skill(skill_id, enabled=payload.enabled, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill '{skill_id}' not found.",
        )
    return {"skill_id": skill_id, "enabled": payload.enabled, "user_id": user_id}
