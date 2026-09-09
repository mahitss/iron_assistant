"""Perception Sources, Scope Authorization, Trust Weighting, and Source Registry (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Set
import uuid

logger = logging.getLogger("kairo.perception.sources")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceType(str, Enum):
    """22 authoritative perception source categories (Spec 3)."""

    DEVICE = "DEVICE"
    DESKTOP = "DESKTOP"
    APPLICATION = "APPLICATION"
    BROWSER = "BROWSER"
    FILE_SYSTEM = "FILE_SYSTEM"
    GIT = "GIT"
    GITHUB = "GITHUB"
    DEPLOYMENT = "DEPLOYMENT"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    API = "API"
    NETWORK = "NETWORK"
    NOTIFICATION = "NOTIFICATION"
    VOICE = "VOICE"
    VISION = "VISION"
    CALENDAR = "CALENDAR"
    AUTOMATION = "AUTOMATION"
    AGENT = "AGENT"
    TASK_ENGINE = "TASK_ENGINE"
    WORLD_MODEL = "WORLD_MODEL"
    USER_INPUT = "USER_INPUT"
    SYSTEM = "SYSTEM"


class PrivacyLevel(str, Enum):
    """Privacy sensitivity classifications governing observation retention and redaction."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    SENSITIVE = "SENSITIVE"
    RESTRICTED = "RESTRICTED"


class SourceStatus(str, Enum):
    """Liveness and operational status of a perception source (Spec 160, 170)."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"
    DISABLED = "DISABLED"


class SourceUnauthorizedError(Exception):
    """Raised when an event or query originates from an unauthorized source scope (Spec 4)."""


@dataclass
class PerceptionSourceScope:
    """Explicitly authorized boundaries for an environmental source (Spec 4, 178-181)."""

    allowed_users: List[str] = field(default_factory=lambda: ["*"])
    allowed_projects: List[str] = field(default_factory=lambda: ["*"])
    allowed_devices: List[str] = field(default_factory=lambda: ["*"])
    allowed_directories: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    require_explicit_consent: bool = False

    def is_authorized(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> bool:
        """Validate if operation belongs to authorized user, project, and device boundaries."""
        if "*" not in self.allowed_users and user_id and user_id not in self.allowed_users:
            return False
        if "*" not in self.allowed_projects and project_id and project_id not in self.allowed_projects:
            return False
        if "*" not in self.allowed_devices and device_id and device_id not in self.allowed_devices:
            return False
        return True

    def is_resource_in_scope(self, resource_path: str) -> bool:
        if not self.allowed_directories:
            return True
        norm = resource_path.replace("\\", "/").lower()
        return any(norm.startswith(d.replace("\\", "/").lower()) for d in self.allowed_directories)


@dataclass
class PerceptionSource:
    """Authorized provider of environmental telemetry and observations (Spec 2, 4, 5)."""

    source_id: str
    type: SourceType
    name: str
    scope: PerceptionSourceScope = field(default_factory=PerceptionSourceScope)
    capabilities: List[str] = field(default_factory=list)
    reliability: float = 1.0  # 0.0 to 1.0 contextual trust (Spec 5)
    status: SourceStatus = SourceStatus.HEALTHY
    last_seen: datetime = field(default_factory=utc_now)
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL

    def validate_authorization(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        device_id: Optional[str] = None,
    ) -> None:
        """Verify that caller has authorization to ingest or query this source (Spec 4)."""
        if self.status == SourceStatus.DISABLED:
            raise SourceUnauthorizedError(f"Source '{self.source_id}' ({self.name}) is DISABLED.")

        if not self.scope.is_authorized(user_id=user_id, project_id=project_id, device_id=device_id):
            raise SourceUnauthorizedError(
                f"Unauthorized access: Source '{self.source_id}' is not authorized for "
                f"user={user_id}, project={project_id}, device={device_id}."
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "type": self.type.value,
            "name": self.name,
            "capabilities": self.capabilities,
            "reliability": self.reliability,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat(),
            "privacy_level": self.privacy_level.value,
            "scope": {
                "allowed_users": self.scope.allowed_users,
                "allowed_projects": self.scope.allowed_projects,
                "allowed_devices": self.scope.allowed_devices,
                "allowed_directories": self.scope.allowed_directories,
                "allowed_domains": self.scope.allowed_domains,
            },
        }


class SourceRegistry:
    """Registry maintaining active and authorized perception sources across all modalities (Spec 2-5)."""

    def __init__(self) -> None:
        # source_id -> PerceptionSource
        self._sources: Dict[str, PerceptionSource] = {}

    def register_source(
        self,
        source_type: SourceType,
        name: str,
        scope: Optional[PerceptionSourceScope] = None,
        capabilities: Optional[List[str]] = None,
        reliability: float = 1.0,
        privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL,
        source_id: Optional[str] = None,
    ) -> PerceptionSource:
        sid = source_id or f"src_{source_type.value.lower()}_{uuid.uuid4().hex[:8]}"
        source = PerceptionSource(
            source_id=sid,
            type=source_type,
            name=name,
            scope=scope or PerceptionSourceScope(),
            capabilities=capabilities or [],
            reliability=max(0.0, min(1.0, reliability)),
            privacy_level=privacy_level,
        )
        self._sources[sid] = source
        logger.info("Registered perception source %s (%s) - type=%s, trust=%.2f", sid, name, source_type.value, reliability)
        return source

    def unregister_source(self, source_id: str) -> bool:
        if source_id in self._sources:
            del self._sources[source_id]
            logger.info("Unregistered perception source %s", source_id)
            return True
        return False

    def get_source(self, source_id: str) -> Optional[PerceptionSource]:
        return self._sources.get(source_id)

    def list_sources(
        self,
        source_type: Optional[SourceType] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[PerceptionSource]:
        res = list(self._sources.values())
        if source_type:
            res = [s for s in res if s.type == source_type]
        if user_id or project_id:
            res = [s for s in res if s.scope.is_authorized(user_id=user_id, project_id=project_id)]
        return res

    def record_heartbeat(self, source_id: str) -> None:
        source = self._sources.get(source_id)
        if source:
            source.last_seen = utc_now()
            if source.status == SourceStatus.OFFLINE:
                source.status = SourceStatus.HEALTHY

    def disable_source(self, source_id: str) -> bool:
        """Enforce Spec 170: Disabling a source marks its state UNKNOWN/UNAVAILABLE; never pretend it's fresh."""
        source = self._sources.get(source_id)
        if not source:
            return False
        source.status = SourceStatus.DISABLED
        source.last_seen = utc_now()
        logger.warning("Disabled perception source %s; observations marked UNAVAILABLE", source_id)
        return True

    def set_status(self, source_id: str, status: SourceStatus) -> None:
        source = self._sources.get(source_id)
        if source:
            source.status = status
            source.last_seen = utc_now()
