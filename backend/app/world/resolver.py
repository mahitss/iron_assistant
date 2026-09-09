"""World context resolution and context packet construction (Task 32, Spec 43-45)."""

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.world.entities import EntityType, WorldEntitySchema
from app.world.freshness import FreshnessPolicy
from app.world.queries import WorldQueryEngine
from app.world.relationships import WorldRelationshipSchema

logger = logging.getLogger("kairo.world.resolver")


class WorldContextItem(BaseModel):
    """Single entity context signal formatted for prompt inclusion."""

    entity_id: str
    type: str
    name: str
    state: str
    epistemic_status: str  # OBSERVED, INFERRED, UNKNOWN, STALE
    confidence: str
    source: str
    observed_at: str
    is_stale: bool


class WorldContextPacket(BaseModel):
    """Structured situational awareness packet for the Context Engine and Task Planner (Spec 44)."""

    summary: str = Field(description="Condensed human-readable situational summary")
    items: list[WorldContextItem] = Field(default_factory=list, description="Targeted entity state items")
    active_tasks_count: int = 0
    connected_devices_count: int = 0
    services_healthy_count: int = 0
    services_unhealthy_count: int = 0
    stale_entities_count: int = 0
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorldContextResolver:
    """Builds bounded, sanitized situational awareness packets for agents and planners."""

    MAX_CONTEXT_ITEMS: int = 15  # Strict prompt budgeting

    @classmethod
    def resolve_world_context(
        cls,
        user_id: str,
        project_id: Optional[str],
        entities: list[WorldEntitySchema],
        relationships: list[WorldRelationshipSchema],
    ) -> WorldContextPacket:
        """Construct a bounded WorldContextPacket for the user/project."""
        now = datetime.now(UTC)
        context_items: list[WorldContextItem] = []

        active_tasks = 0
        connected_devices = 0
        services_healthy = 0
        services_unhealthy = 0
        stale_count = 0

        # Filter relevant entities
        relevant_entities: list[WorldEntitySchema] = []
        for e in entities:
            if e.owner_id != user_id:
                continue

            # Check staleness
            is_stale = FreshnessPolicy.is_stale(e.observed_at, e.expires_at, e.type, now=now)
            if is_stale:
                stale_count += 1

            # Determine epistemic status label (Spec 45)
            if is_stale:
                status_label = "STALE"
            elif e.state.upper() == "UNKNOWN":
                status_label = "UNKNOWN"
            else:
                status_label = e.observation_type.value

            # Counters
            if e.type == EntityType.TASK and e.state.upper() in ("RUNNING", "QUEUED", "PLANNING", "WAITING_APPROVAL"):
                active_tasks += 1
            elif e.type == EntityType.DEVICE and e.state.upper() == "CONNECTED":
                connected_devices += 1
            elif e.type == EntityType.SERVICE:
                if e.state.upper() == "HEALTHY":
                    services_healthy += 1
                elif e.state.upper() in ("DEGRADED", "UNHEALTHY"):
                    services_unhealthy += 1

            # Match project or global resources
            if project_id and e.project_id == project_id:
                relevant_entities.append(e)
            elif not project_id or e.type in (EntityType.DEVICE, EntityType.SERVICE, EntityType.MODEL):
                relevant_entities.append(e)

            context_items.append(
                WorldContextItem(
                    entity_id=e.id,
                    type=e.type.value,
                    name=e.name,
                    state=e.state,
                    epistemic_status=status_label,
                    confidence=e.confidence.value,
                    source=e.source,
                    observed_at=e.observed_at.isoformat(),
                    is_stale=is_stale,
                )
            )

        # Build concise situational narrative
        summary_parts = []
        if project_id:
            summary_parts.append(f"Project context: {project_id}.")
        summary_parts.append(f"Environment: {connected_devices} connected device(s), {active_tasks} active task(s).")
        if services_unhealthy > 0:
            summary_parts.append(f"⚠️ {services_unhealthy} service(s) currently degraded/unhealthy.")
        if stale_count > 0:
            summary_parts.append(f"ℹ️ {stale_count} entity observation(s) marked stale.")

        summary_text = " ".join(summary_parts)

        return WorldContextPacket(
            summary=summary_text,
            items=context_items[:cls.MAX_CONTEXT_ITEMS],
            active_tasks_count=active_tasks,
            connected_devices_count=connected_devices,
            services_healthy_count=services_healthy,
            services_unhealthy_count=services_unhealthy,
            stale_entities_count=stale_count,
            resolved_at=now,
        )
