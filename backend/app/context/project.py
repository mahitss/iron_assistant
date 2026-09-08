"""Project service handling database persistence, ownership verification, and resource linking."""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.context.models import (
    Project,
    ProjectConversation,
    ProjectRepository,
    ProjectWorkflow,
)
from app.context.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdate,
)

logger = logging.getLogger("kairo.context.project")


class ProjectService:
    """Manages project lifecycles and relationship links with strict user ownership validation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_project(self, user_id: str, payload: ProjectCreate) -> ProjectResponse:
        """Create a new project owned by user."""
        proj = Project(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            status=payload.status.value,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_active_at=datetime.now(UTC),
        )
        self.session.add(proj)
        await self.session.commit()
        await self.session.refresh(proj)
        return self._to_response(proj)

    async def get_project(self, user_id: str, project_id: str) -> ProjectResponse | None:
        """Retrieve project if owned by user."""
        stmt = (
            select(Project)
            .where(Project.id == project_id, Project.user_id == user_id)
            .options(
                selectinload(Project.repositories),
                selectinload(Project.workflows),
                selectinload(Project.conversations),
            )
        )
        result = await self.session.execute(stmt)
        proj = result.scalar_one_or_none()
        return self._to_response(proj) if proj else None

    async def get_project_by_name(self, user_id: str, name: str) -> ProjectResponse | None:
        """Find project by name (case-insensitive) for given user."""
        stmt = (
            select(Project)
            .where(Project.user_id == user_id, Project.name.ilike(name.strip()))
            .options(
                selectinload(Project.repositories),
                selectinload(Project.workflows),
                selectinload(Project.conversations),
            )
        )
        result = await self.session.execute(stmt)
        proj = result.scalar_one_or_none()
        return self._to_response(proj) if proj else None

    async def list_projects(
        self,
        user_id: str,
        status: ProjectStatus | str | None = None,
        limit: int = 50,
    ) -> list[ProjectResponse]:
        """List user's projects with optional status filter, ordered by recency."""
        stmt = (
            select(Project)
            .where(Project.user_id == user_id)
            .options(
                selectinload(Project.repositories),
                selectinload(Project.workflows),
                selectinload(Project.conversations),
            )
            .order_by(Project.last_active_at.desc())
            .limit(limit)
        )
        if status:
            val = status.value if isinstance(status, ProjectStatus) else str(status)
            stmt = stmt.where(Project.status == val)

        result = await self.session.execute(stmt)
        projects = result.scalars().all()
        return [self._to_response(p) for p in projects]

    async def update_project(
        self,
        user_id: str,
        project_id: str,
        updates: ProjectUpdate,
    ) -> ProjectResponse | None:
        """Update metadata or status of user's project."""
        stmt = select(Project).where(Project.id == project_id, Project.user_id == user_id)
        result = await self.session.execute(stmt)
        proj = result.scalar_one_or_none()
        if not proj:
            return None

        if updates.name is not None:
            proj.name = updates.name.strip()
        if updates.description is not None:
            proj.description = updates.description.strip()
        if updates.status is not None:
            proj.status = updates.status.value

        proj.updated_at = datetime.now(UTC)
        proj.last_active_at = datetime.now(UTC)

        await self.session.commit()
        return await self.get_project(user_id, project_id)

    async def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete user's project and cascaded links."""
        stmt = delete(Project).where(Project.id == project_id, Project.user_id == user_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def touch_project(self, user_id: str, project_id: str) -> None:
        """Bump last_active_at timestamp for project."""
        stmt = (
            update(Project)
            .where(Project.id == project_id, Project.user_id == user_id)
            .values(last_active_at=datetime.now(UTC))
        )
        await self.session.execute(stmt)
        await self.session.commit()

    # --- Resource Links ---

    async def link_repository(
        self,
        user_id: str,
        project_id: str,
        repository_path: str,
        is_primary: bool = False,
    ) -> bool:
        """Associate a repository with a project."""
        proj = await self.get_project(user_id, project_id)
        if not proj:
            return False

        link = ProjectRepository(
            id=str(uuid.uuid4()),
            project_id=project_id,
            repository_path=repository_path.strip(),
            is_primary=is_primary,
            created_at=datetime.now(UTC),
        )
        self.session.add(link)
        await self.session.commit()
        return True

    async def link_workflow(self, user_id: str, project_id: str, workflow_id: str) -> bool:
        """Associate an automated workflow with a project."""
        proj = await self.get_project(user_id, project_id)
        if not proj:
            return False

        link = ProjectWorkflow(
            id=str(uuid.uuid4()),
            project_id=project_id,
            workflow_id=workflow_id,
            created_at=datetime.now(UTC),
        )
        self.session.add(link)
        await self.session.commit()
        return True

    async def link_conversation(self, user_id: str, project_id: str, conversation_id: str) -> bool:
        """Associate a conversation thread with a project."""
        proj = await self.get_project(user_id, project_id)
        if not proj:
            return False

        link = ProjectConversation(
            id=str(uuid.uuid4()),
            project_id=project_id,
            conversation_id=conversation_id,
            created_at=datetime.now(UTC),
        )
        self.session.add(link)
        await self.session.commit()
        return True

    @staticmethod
    def _to_response(proj: Project) -> ProjectResponse:
        """Convert SQLAlchemy Project model to Pydantic ProjectResponse."""
        repos = [r.repository_path for r in getattr(proj, "repositories", []) or []]
        wfs = [w.workflow_id for w in getattr(proj, "workflows", []) or []]
        convs = [c.conversation_id for c in getattr(proj, "conversations", []) or []]

        return ProjectResponse(
            id=proj.id,
            user_id=proj.user_id,
            name=proj.name,
            description=proj.description,
            status=ProjectStatus(proj.status),
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            last_active_at=proj.last_active_at,
            repositories=repos,
            workflows=wfs,
            conversations=convs,
        )
