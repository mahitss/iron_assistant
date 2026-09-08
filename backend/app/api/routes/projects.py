"""REST API endpoints for Project management and resource associations."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.project import ProjectService
from app.context.schemas import (
    ProjectCreate,
    ProjectRepositoryLink,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
    ProjectWorkflowLink,
)
from app.db.session import get_db_session

logger = logging.getLogger("kairo.api.projects")

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Extract authenticated user ID from request header."""
    if not x_user_id or not x_user_id.strip():
        return "default_user"
    return x_user_id.strip()


def get_project_service(db: AsyncSession | None = Depends(get_db_session)) -> ProjectService:
    """Inject ProjectService dependency."""
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is currently unavailable.",
        )
    return ProjectService(db)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    payload: ProjectCreate,
    user_id: str = Depends(get_current_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Create a new project workspace owned by the authenticated user."""
    return await service.create_project(user_id=user_id, payload=payload)


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List user projects",
)
async def list_projects(
    status_filter: ProjectStatus | None = Query(default=None, alias="status", description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    """Retrieve user's projects ordered by recent activity."""
    return await service.list_projects(user_id=user_id, status=status_filter, limit=limit)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID",
)
async def get_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Retrieve details and linked resources for a specific project."""
    proj = await service.get_project(user_id=user_id, project_id=project_id)
    if not proj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return proj


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project metadata or status",
)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    user_id: str = Depends(get_current_user_id),
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """Update name, description, or lifecycle status of user's project."""
    updated = await service.update_project(user_id=user_id, project_id=project_id, updates=payload)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return updated


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
async def delete_project(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    service: ProjectService = Depends(get_project_service),
) -> None:
    """Permanently delete project and cascaded resource associations."""
    deleted = await service.delete_project(user_id=user_id, project_id=project_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )


@router.post(
    "/{project_id}/repositories",
    status_code=status.HTTP_201_CREATED,
    summary="Link repository to project",
)
async def link_repository(
    project_id: str,
    payload: ProjectRepositoryLink,
    user_id: str = Depends(get_current_user_id),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, str]:
    """Associate a repository path with a project."""
    success = await service.link_repository(
        user_id=user_id,
        project_id=project_id,
        repository_path=payload.repository_path,
        is_primary=payload.is_primary,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return {"status": "linked", "project_id": project_id, "repository": payload.repository_path}


@router.post(
    "/{project_id}/workflows",
    status_code=status.HTTP_201_CREATED,
    summary="Link workflow to project",
)
async def link_workflow(
    project_id: str,
    payload: ProjectWorkflowLink,
    user_id: str = Depends(get_current_user_id),
    service: ProjectService = Depends(get_project_service),
) -> dict[str, str]:
    """Associate an automated workflow with a project."""
    success = await service.link_workflow(
        user_id=user_id,
        project_id=project_id,
        workflow_id=payload.workflow_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )
    return {"status": "linked", "project_id": project_id, "workflow_id": payload.workflow_id}
