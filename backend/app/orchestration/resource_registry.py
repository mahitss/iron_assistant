"""Resource Registry managing capacity, reservations, allocations, and leak detection (Task 59)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.orchestration.resources import create_reservation, create_resource
from app.orchestration.safety import (
    OrchestrationSafetyError,
    ResourceContentionError,
)
from app.orchestration.schemas import (
    HealthStatus,
    ResourceDefinition,
    ResourceReservation,
    ResourceStatus,
    ResourceType,
)

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """Registry maintaining available resources, quotas, capacity tracking, and reservations."""

    def __init__(self) -> None:
        self._resources: dict[str, ResourceDefinition] = {}
        self._reservations: dict[str, ResourceReservation] = {}

    def register(self, resource: ResourceDefinition, allow_override: bool = False) -> None:
        """Register a resource."""
        if resource.resource_id in self._resources and not allow_override:
            raise OrchestrationSafetyError(
                f"Resource with ID '{resource.resource_id}' is already registered."
            )
        self._resources[resource.resource_id] = resource
        logger.info("RESOURCE_REGISTERED: id=%s name=%s capacity=%s", resource.resource_id, resource.name, resource.total_capacity)

    def get(self, resource_id: str) -> ResourceDefinition:
        """Retrieve resource by ID."""
        res = self._resources.get(resource_id)
        if not res:
            raise OrchestrationSafetyError(f"Resource with ID '{resource_id}' not found.")
        return res

    def has_resource(self, resource_id: str) -> bool:
        return resource_id in self._resources

    def list_all(
        self,
        environment: str | None = None,
        resource_type: ResourceType | None = None,
    ) -> list[ResourceDefinition]:
        """List resources optionally filtered by environment and resource type."""
        # First clean up any expired reservations so capacity is accurate
        self.clean_expired_reservations()

        results = list(self._resources.values())
        if environment:
            env_clean = environment.strip().lower()
            results = [r for r in results if r.environment.lower() == env_clean]
        if resource_type:
            results = [r for r in results if r.resource_type == resource_type]
        return results

    def reserve(
        self,
        resource_id: str,
        owner: str,
        purpose: str,
        amount: float,
        expires_at: datetime,
        scope: str = "GLOBAL",
        authorization_signature: str | None = None,
    ) -> ResourceReservation:
        """Reserve resource capacity with expiry and ownership isolation."""
        self.clean_expired_reservations()
        res = self.get(resource_id)

        # Health check
        if res.health in (HealthStatus.UNAVAILABLE, HealthStatus.UNKNOWN):
            raise ResourceContentionError(
                f"Cannot reserve resource '{res.name}': resource health is {res.health.value}."
            )

        if res.available_capacity < amount:
            raise ResourceContentionError(
                f"Insufficient capacity for '{res.name}': requested {amount}, available {res.available_capacity}."
            )

        reservation = create_reservation(
            resource_id=resource_id,
            owner=owner,
            purpose=purpose,
            amount=amount,
            expires_at=expires_at,
            scope=scope,
            authorization_signature=authorization_signature,
        )

        res.available_capacity -= amount
        res.reserved_capacity += amount
        self._update_status(res)
        self._reservations[reservation.reservation_id] = reservation

        logger.info(
            "RESOURCE_RESERVED: res_id=%s rsv_id=%s amount=%s owner=%s expires=%s",
            resource_id,
            reservation.reservation_id,
            amount,
            owner,
            expires_at.isoformat(),
        )
        return reservation

    def release_reservation(self, reservation_id: str) -> bool:
        """Release an active reservation and restore available capacity."""
        rsv = self._reservations.get(reservation_id)
        if not rsv or not rsv.is_active:
            return False

        if rsv.resource_id in self._resources:
            res = self._resources[rsv.resource_id]
            res.reserved_capacity = max(0.0, res.reserved_capacity - rsv.amount)
            res.available_capacity = min(res.total_capacity, res.available_capacity + rsv.amount)
            self._update_status(res)

        rsv.is_active = False
        logger.info("RESERVATION_RELEASED: rsv_id=%s amount=%s", reservation_id, rsv.amount)
        return True

    def allocate(
        self,
        resource_id: str,
        amount: float,
        reservation_id: str | None = None,
        owner: str | None = None,
    ) -> bool:
        """Allocate resource capacity for immediate task execution."""
        self.clean_expired_reservations()
        res = self.get(resource_id)

        if amount <= 0:
            return True

        if reservation_id:
            rsv = self._reservations.get(reservation_id)
            if not rsv or not rsv.is_active:
                raise ResourceContentionError(f"Reservation '{reservation_id}' is invalid or expired.")
            if owner and rsv.owner != owner:
                raise OrchestrationSafetyError(
                    f"Resource isolation violation: Owner '{owner}' cannot claim reservation owned by '{rsv.owner}'."
                )
            if rsv.amount < amount:
                raise ResourceContentionError(
                    f"Reservation amount {rsv.amount} is less than requested allocation {amount}."
                )
            # Convert reserved capacity to allocated capacity
            rsv.amount -= amount
            res.reserved_capacity = max(0.0, res.reserved_capacity - amount)
            res.allocated_capacity += amount
            if rsv.amount <= 0:
                rsv.is_active = False
        else:
            if res.available_capacity < amount:
                raise ResourceContentionError(
                    f"Insufficient capacity for '{res.name}': requested {amount}, available {res.available_capacity}."
                )
            res.available_capacity -= amount
            res.allocated_capacity += amount

        self._update_status(res)
        logger.info("RESOURCE_ALLOCATED: res_id=%s amount=%s", resource_id, amount)
        return True

    def release_allocation(self, resource_id: str, amount: float) -> bool:
        """Release allocated capacity upon task completion."""
        if resource_id not in self._resources or amount <= 0:
            return False

        res = self._resources[resource_id]
        released = min(res.allocated_capacity, amount)
        res.allocated_capacity = max(0.0, res.allocated_capacity - released)
        res.available_capacity = min(res.total_capacity, res.available_capacity + released)
        self._update_status(res)
        logger.info("RESOURCE_DEALLOCATED: res_id=%s released=%s", resource_id, released)
        return True

    def clean_expired_reservations(self) -> int:
        """Identify and release all expired reservations to prevent capacity leakage."""
        now = datetime.now(timezone.utc)
        cleaned_count = 0
        for rsv in list(self._reservations.values()):
            if rsv.is_active and rsv.expires_at <= now:
                self.release_reservation(rsv.reservation_id)
                cleaned_count += 1
        if cleaned_count > 0:
            logger.info("CLEANED_EXPIRED_RESERVATIONS: count=%d", cleaned_count)
        return cleaned_count

    def detect_leaks(self) -> list[dict[str, Any]]:
        """Audit registry for abandoned reservations, negative capacity, or orphans."""
        leaks = []
        now = datetime.now(timezone.utc)

        # Check for expired but marked active
        for rsv in self._reservations.values():
            if rsv.is_active and rsv.expires_at <= now:
                leaks.append({
                    "type": "EXPIRED_UNRELEASED_RESERVATION",
                    "reservation_id": rsv.reservation_id,
                    "resource_id": rsv.resource_id,
                    "owner": rsv.owner,
                    "amount": rsv.amount,
                    "expired_at": rsv.expires_at.isoformat(),
                })

        # Check capacity arithmetic anomalies
        for res in self._resources.values():
            expected_avail = res.total_capacity - (res.allocated_capacity + res.reserved_capacity)
            if abs(res.available_capacity - expected_avail) > 1e-4:
                leaks.append({
                    "type": "CAPACITY_CALCULATION_DRIFT",
                    "resource_id": res.resource_id,
                    "name": res.name,
                    "current_available": res.available_capacity,
                    "expected_available": expected_avail,
                })

        return leaks

    def _update_status(self, res: ResourceDefinition) -> None:
        """Update ResourceStatus based on available capacity and health."""
        if res.health in (HealthStatus.UNAVAILABLE, HealthStatus.BLOCKED):
            res.status = ResourceStatus.UNAVAILABLE
        elif res.health == HealthStatus.DEGRADED:
            res.status = ResourceStatus.DEGRADED
        elif res.available_capacity <= 0:
            res.status = ResourceStatus.EXHAUSTED
        elif res.available_capacity < (res.total_capacity * 0.2):
            res.status = ResourceStatus.LIMITED
        elif res.reserved_capacity > 0 and res.allocated_capacity == 0:
            res.status = ResourceStatus.RESERVED
        elif res.allocated_capacity > 0:
            res.status = ResourceStatus.ALLOCATED
        else:
            res.status = ResourceStatus.AVAILABLE

    def populate_defaults(self) -> None:
        """Initialize standard resources across environments."""
        defaults = [
            ("Production Compute Cluster", ResourceType.COMPUTE, "AWS", 100.0, "vCPU", "production", 0.05),
            ("Staging Compute Cluster", ResourceType.COMPUTE, "AWS", 50.0, "vCPU", "staging", 0.02),
            ("Dev Local Compute", ResourceType.COMPUTE, "Local", 20.0, "vCPU", "development", 0.0),
            ("Production DB Connections", ResourceType.DATABASE, "PostgreSQL", 100.0, "connections", "production", 0.01),
            ("Staging DB Connections", ResourceType.DATABASE, "PostgreSQL", 50.0, "connections", "staging", 0.005),
            ("OpenRouter API Quota", ResourceType.QUOTA, "OpenRouter", 1000.0, "requests/min", "production", 0.0),
            ("Agent Execution Slots", ResourceType.EXECUTION_SLOT, "Kairo", 10.0, "slots", "production", 0.0),
        ]
        for name, rtype, prov, cap, unit, env, cost in defaults:
            rid = f"res_{name.lower().replace(' ', '_')}"
            if rid not in self._resources:
                res = create_resource(
                    name=name,
                    resource_type=rtype,
                    provider=prov,
                    total_capacity=cap,
                    unit=unit,
                    environment=env,
                    cost_rate=cost,
                    resource_id=rid,
                )
                self.register(res, allow_override=True)


default_resource_registry = ResourceRegistry()
default_resource_registry.populate_defaults()
