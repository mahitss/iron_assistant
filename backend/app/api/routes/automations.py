"""API routes for Kairo Automation and Workflow Engine."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.safety import AutomationSecurityError
from app.automation.schemas import (
    ApprovalDecisionRequest,
    ApprovalRequestResponse,
    NotificationResponse,
    WorkflowCreate,
    WorkflowResponse,
    WorkflowRunResponse,
    WorkflowUpdate,
)
from app.automation.service import AutomationService
from app.core.config import get_settings
from app.db.session import get_db_session

logger = logging.getLogger("kairo.api.automations")

router = APIRouter(prefix="/automations", tags=["Automations & Workflows"])


def get_current_user_id(x_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None) -> str:
    """Extract authenticated user_id from header (defaults to 'default_user')."""
    return x_user_id.strip() if x_user_id and x_user_id.strip() else "default_user"


def get_automation_service(db: AsyncSession | None = Depends(get_db_session)) -> AutomationService:
    """Dependency injecting AutomationService with active DB session."""
    settings = get_settings()
    if not settings.KAIRO_AUTOMATION_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Automation system is currently disabled by configuration.",
        )
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured. Automation engine is inactive.",
        )
    return AutomationService(session=db, settings=settings)


# --- Workflow CRUD ---

@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> WorkflowResponse:
    """Create a new durable workflow definition."""
    try:
        wf = await service.create_workflow(user_id=user_id, data=payload)
        return WorkflowResponse.model_validate(wf, from_attributes=True)
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> list[WorkflowResponse]:
    """List all workflows owned by the current user."""
    workflows = await service.list_workflows(user_id=user_id)
    return [WorkflowResponse.model_validate(w, from_attributes=True) for w in workflows]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> WorkflowResponse:
    """Get metadata for a specific workflow."""
    try:
        wf = await service.get_workflow(workflow_id=workflow_id, user_id=user_id)
        return WorkflowResponse.model_validate(wf, from_attributes=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> WorkflowResponse:
    """Update workflow parameters or toggle enabled state."""
    try:
        wf = await service.update_workflow(workflow_id=workflow_id, user_id=user_id, data=payload)
        return WorkflowResponse.model_validate(wf, from_attributes=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> None:
    """Delete a workflow."""
    try:
        await service.delete_workflow(workflow_id=workflow_id, user_id=user_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


# --- Manual Run & Execution ---

@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_workflow_manually(
    workflow_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> WorkflowRunResponse:
    """Trigger an immediate execution run of a workflow."""
    try:
        run = await service.run_workflow_manually(workflow_id=workflow_id, user_id=user_id)
        # Reload with steps/approvals
        detailed_run = await service.get_workflow_run(run.id, user_id)
        return WorkflowRunResponse.model_validate(detailed_run, from_attributes=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/{workflow_id}/runs", response_model=list[WorkflowRunResponse])
async def list_workflow_runs(
    workflow_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> list[WorkflowRunResponse]:
    """List execution runs for a specific workflow."""
    try:
        runs = await service.list_workflow_runs(workflow_id=workflow_id, user_id=user_id)
        return [WorkflowRunResponse.model_validate(r, from_attributes=True) for r in runs]
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    run_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> WorkflowRunResponse:
    """Inspect execution details and step results for a specific run."""
    try:
        run = await service.get_workflow_run(run_id=run_id, user_id=user_id)
        return WorkflowRunResponse.model_validate(run, from_attributes=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/{workflow_id}/cancel", response_model=WorkflowRunResponse)
async def cancel_workflow_run(
    workflow_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> WorkflowRunResponse:
    """Cancel any active execution run for a workflow."""
    try:
        run = await service.cancel_run(workflow_id=workflow_id, user_id=user_id)
        return WorkflowRunResponse.model_validate(run, from_attributes=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AutomationSecurityError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


# --- Approvals ---

@router.get("/approvals/pending", response_model=list[ApprovalRequestResponse])
async def list_pending_approvals(
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> list[ApprovalRequestResponse]:
    """List pending human-in-the-loop approvals awaiting user decision."""
    approvals = await service.list_pending_approvals(user_id=user_id)
    return [ApprovalRequestResponse.model_validate(a, from_attributes=True) for a in approvals]


@router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestResponse)
async def approve_action(
    approval_id: str,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> ApprovalRequestResponse:
    """Approve a pending restricted action and resume workflow execution."""
    try:
        appr = await service.decide_approval(approval_id=approval_id, user_id=user_id, decision="approve")
        return ApprovalRequestResponse.model_validate(appr, from_attributes=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/deny", response_model=ApprovalRequestResponse)
async def deny_action(
    approval_id: str,
    payload: ApprovalDecisionRequest | None = None,
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> ApprovalRequestResponse:
    """Deny a pending restricted action and fail the workflow run."""
    try:
        reason = payload.reason if payload else "Denied by user"
        appr = await service.decide_approval(
            approval_id=approval_id, user_id=user_id, decision="deny", reason=reason
        )
        return ApprovalRequestResponse.model_validate(appr, from_attributes=True)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# --- Notifications ---

@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    user_id: str = Depends(get_current_user_id),
    service: AutomationService = Depends(get_automation_service),
) -> list[NotificationResponse]:
    """List in-app alerts produced by workflows."""
    notifs = await service.list_notifications(user_id=user_id)
    return [NotificationResponse.model_validate(n, from_attributes=True) for n in notifs]
