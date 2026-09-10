"""Resource modeling, capacity tracking, reservations, and lifecycle rules for Orchestration (Task 59)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.orchestration.safety import OrchestrationSafetyError, sanitize_orchestration_directive
from app.orchestration.schemas import (
    HealthStatus,
    ResourceDefinition,
    ResourceReservation,
    ResourceStatus,
    ResourceType,
)

logger = logging.getLogger(__name__)


def create_resource(
    name: str,
    resource_type: ResourceType = ResourceType.COMPUTE,
    provider: str = "SYSTEM",
    total_capacity: float = 100.0,
    unit: str = "units",
    environment: str = "development",
    health: HealthStatus = HealthStatus.HEALTHY,
    cost_rate: float = 0.0,
    constraints: dict[str, Any] | None = None,
    ownership: str = "SYSTEM",
    resource_id: str | None = None,
) -> ResourceDefinition:
    """Create and validate a new ResourceDefinition."""
    clean_name = sanitize_orchestration_directive(name)
    rid = resource_id or f"res_{clean_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"

    total = max(0.0, float(total_capacity))
    return ResourceDefinition(
        resource_id=rid,
        name=clean_name,
        resource_type=resource_type,
        provider=provider,
        total_capacity=total,
        available_capacity=total,
        allocated_capacity=0.0,
        reserved_capacity=0.0,
        unit=unit,
        environment=environment.lower(),
        health=health,
        cost_rate=max(0.0, float(cost_rate)),
        constraints=constraints or {},
        ownership=ownership,
        status=ResourceStatus.AVAILABLE if health == HealthStatus.HEALTHY else ResourceStatus.DEGRADED,
    )


def create_reservation(
    resource_id: str,
    owner: str,
    purpose: str,
    amount: float,
    expires_at: datetime,
    scope: str = "GLOBAL",
    reservation_id: str | None = None,
    authorization_signature: str | None = None,
) -> ResourceReservation:
    """Create a resource reservation with explicit expiry and owner."""
    if amount <= 0:
        raise OrchestrationSafetyError("Reservation amount must be strictly positive.")

    clean_purpose = sanitize_orchestration_directive(purpose)
    rsv_id = reservation_id or f"rsv_{uuid.uuid4().hex[:8]}"

    # Expiry must be in UTC
    exp_utc = expires_at.astimezone(timezone.utc) if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)

    return ResourceReservation(
        reservation_id=rsv_id,
        resource_id=resource_id,
        owner=owner,
        purpose=clean_purpose,
        scope=scope,
        amount=float(amount),
        is_active=True,
        authorization_signature=authorization_signature,
        expires_at=exp_utc,
    )
