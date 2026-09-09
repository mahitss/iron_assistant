"""Scoped agent workspace and structured shared artifact registry (Task 44)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional, Union
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.security.redaction import ArgumentSanitizer

logger = logging.getLogger("kairo.agents.workspace")


def utc_now() -> datetime:
    return datetime.now(UTC)


class ArtifactConflictError(Exception):
    """Raised when an agent attempts to silently overwrite or mutate a shared artifact."""


@dataclass
class CollaborativeArtifact:
    """A versioned, structured artifact published to the shared team workspace (Specs 25, 164, 165)."""

    artifact_id: str
    title: str
    content: Union[dict[str, Any], str]
    collaboration_id: str = "default_session"
    creator_agent_id: str = ""
    creator_id: str = ""
    contract_id: str | None = None
    artifact_type: str = "general"
    version: int = 1
    content_hash: str = ""
    scope: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.creator_id and not self.creator_agent_id:
            self.creator_agent_id = self.creator_id
        elif self.creator_agent_id and not self.creator_id:
            self.creator_id = self.creator_agent_id

        if not self.content_hash:
            if isinstance(self.content, str):
                raw = self.content
            else:
                raw = json.dumps(self.content, sort_keys=True)
            self.content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "collaboration_id": self.collaboration_id,
            "creator_agent_id": self.creator_agent_id,
            "contract_id": self.contract_id,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "content": self.content,
            "version": self.version,
            "content_hash": self.content_hash,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
        }


class AgentWorkspace:
    """Individual, scoped workspace for an agent during task execution (Spec 24)."""

    def __init__(
        self,
        agent_id: str,
        contract_id: str,
        project_id: str = "default_project",
        allowed_resources: list[str] | None = None,
        authorized_knowledge: list[dict[str, Any]] | None = None,
        authorized_files: list[str] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.contract_id = contract_id
        self.project_id = project_id
        self.allowed_resources = allowed_resources or []
        self.authorized_knowledge = authorized_knowledge or []
        self.authorized_files = authorized_files or []
        self._local_scratchpad: dict[str, Any] = {}

    def write_scratchpad(self, key: str, value: Any) -> None:
        self._local_scratchpad[key] = ArgumentSanitizer.sanitize(value)

    def read_scratchpad(self, key: str) -> Any:
        return self._local_scratchpad.get(key)

    def add_context_item(self, key: str, value: Any) -> None:
        self.write_scratchpad(key, value)

    def get_context_item(self, key: str) -> Any:
        return self.read_scratchpad(key)

    def can_access_resource(self, resource: str) -> bool:
        if not self.allowed_resources:
            return False
        if "*" in self.allowed_resources:
            return True
        for allowed in self.allowed_resources:
            if resource == allowed or resource.startswith(allowed):
                return True
        return False


class SharedTeamWorkspace:
    """Collaborative shared workspace publishing structured versioned artifacts (Specs 25, 26, 164-167)."""

    def __init__(self, session_id: str = "default_session") -> None:
        self.session_id = session_id
        # artifact_id -> list of versions
        self._artifacts: dict[str, list[CollaborativeArtifact]] = {}
        # (collaboration_id, title) -> list of versioned artifacts
        self._title_index: dict[tuple[str, str], list[CollaborativeArtifact]] = {}

    def publish_artifact(
        self,
        artifact_or_session: Union[CollaborativeArtifact, str],
        creator_agent_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        title: Optional[str] = None,
        content: Optional[Any] = None,
        contract_id: Optional[str] = None,
        scope: Optional[dict[str, Any]] = None,
    ) -> CollaborativeArtifact:
        """Publish an artifact with versioning and conflict protection."""
        if isinstance(artifact_or_session, CollaborativeArtifact):
            artifact = artifact_or_session
            # Check for silent overwrite on identical version
            existing_versions = self._artifacts.get(artifact.artifact_id, [])
            for ev in existing_versions:
                if ev.version == artifact.version:
                    raise ValueError(
                        f"Cannot overwrite artifact '{artifact.artifact_id}' with identical version {artifact.version}."
                    )
            self._artifacts.setdefault(artifact.artifact_id, []).append(artifact)
            return artifact

        # Keyword invocation
        collaboration_id = str(artifact_or_session)
        clean_content = ArgumentSanitizer.sanitize(content or {})
        index_key = (collaboration_id, (title or "").strip().lower())
        existing = self._title_index.get(index_key, [])
        version = len(existing) + 1

        artifact = CollaborativeArtifact(
            artifact_id=f"art_{uuid.uuid4().hex[:10]}",
            collaboration_id=collaboration_id,
            creator_agent_id=creator_agent_id or "unknown",
            contract_id=contract_id,
            artifact_type=artifact_type or "general",
            title=title or "Untitled",
            content=clean_content,
            version=version,
            scope=scope or {},
        )
        self._artifacts.setdefault(artifact.artifact_id, []).append(artifact)
        self._title_index.setdefault(index_key, []).append(artifact)
        return artifact

    def get_latest_artifact(self, artifact_id: str) -> CollaborativeArtifact | None:
        versions = self._artifacts.get(artifact_id, [])
        return versions[-1] if versions else None

    def get_artifact(self, artifact_id: str) -> CollaborativeArtifact | None:
        return self.get_latest_artifact(artifact_id)

    def list_artifacts(
        self,
        collaboration_id: Optional[str] = None,
        artifact_type: str | None = None,
    ) -> list[CollaborativeArtifact]:
        collab_id = collaboration_id or self.session_id
        all_latest = [versions[-1] for versions in self._artifacts.values() if versions and versions[-1].collaboration_id == collab_id]
        if artifact_type:
            all_latest = [a for a in all_latest if a.artifact_type.lower() == artifact_type.lower()]
        return all_latest
