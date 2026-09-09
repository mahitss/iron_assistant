"""Environment Snapshots, Consistency Models, and Partial State Handling (Task 46)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger("kairo.perception.snapshots")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class EnvironmentSnapshot:
    """Bounded, time-versioned state representation of the environment (Spec 31-35)."""

    snapshot_id: str
    version: int
    environment: str
    timestamp: datetime = field(default_factory=utc_now)
    devices: Dict[str, Any] = field(default_factory=dict)
    apps: Dict[str, Any] = field(default_factory=dict)
    services: Dict[str, Any] = field(default_factory=dict)
    repositories: Dict[str, Any] = field(default_factory=dict)
    deployments: Dict[str, Any] = field(default_factory=dict)
    tasks: Dict[str, Any] = field(default_factory=dict)
    agents: Dict[str, Any] = field(default_factory=dict)
    is_atomic: bool = True  # Distinguishes atomic from best-effort (Spec 33)
    missing_sources: List[str] = field(default_factory=list)  # Spec 34

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "version": self.version,
            "environment": self.environment,
            "timestamp": self.timestamp.isoformat(),
            "devices": self.devices,
            "apps": self.apps,
            "services": self.services,
            "repositories": self.repositories,
            "deployments": self.deployments,
            "tasks": self.tasks,
            "agents": self.agents,
            "is_atomic": self.is_atomic,
            "missing_sources": self.missing_sources,
        }


class SnapshotManager:
    """Builds and versions environment snapshots with zero fabricated state (Spec 31-35)."""

    def __init__(self) -> None:
        # environment -> list of snapshots in chronological order
        self._history: Dict[str, List[EnvironmentSnapshot]] = {}

    def create_snapshot(
        self,
        environment: str,
        devices: Optional[Dict[str, Any]] = None,
        apps: Optional[Dict[str, Any]] = None,
        services: Optional[Dict[str, Any]] = None,
        repositories: Optional[Dict[str, Any]] = None,
        deployments: Optional[Dict[str, Any]] = None,
        tasks: Optional[Dict[str, Any]] = None,
        agents: Optional[Dict[str, Any]] = None,
        is_atomic: bool = True,
        missing_sources: Optional[List[str]] = None,
    ) -> EnvironmentSnapshot:
        """Create versioned snapshot. Unavailable sources become UNKNOWN, never fabricated (Spec 34, 35)."""
        env_upper = environment.upper()
        history = self._history.setdefault(env_upper, [])
        version = len(history) + 1
        sid = f"snap_{env_upper.lower()}_v{version}_{uuid.uuid4().hex[:8]}"

        # Treat missing sources as UNKNOWN, not HEALTHY (Spec 35)
        clean_services = dict(services or {})
        for missing in (missing_sources or []):
            if missing not in clean_services:
                clean_services[missing] = {"status": "UNKNOWN", "reliability": 0.0}

        snap = EnvironmentSnapshot(
            snapshot_id=sid,
            version=version,
            environment=env_upper,
            devices=devices or {},
            apps=apps or {},
            services=clean_services,
            repositories=repositories or {},
            deployments=deployments or {},
            tasks=tasks or {},
            agents=agents or {},
            is_atomic=is_atomic,
            missing_sources=missing_sources or [],
        )
        history.append(snap)
        logger.info("Captured %s snapshot %s (v%d, missing=%s)", env_upper, sid, version, missing_sources or [])
        return snap

    def get_latest_snapshot(self, environment: str) -> Optional[EnvironmentSnapshot]:
        history = self._history.get(environment.upper(), [])
        return history[-1] if history else None
