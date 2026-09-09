"""Central unified State Fabric coordinator (Task 39, Spec 1, 147-148)."""

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.observability.sanitization import TelemetrySanitizer
from app.state.cache import ScopedStateCache, scoped_cache
from app.state.changelog import StateChangelog, state_changelog
from app.state.invalidation import CacheInvalidator, cache_invalidator
from app.state.ownership import DomainOwnershipRegistry
from app.state.quarantine import StateQuarantineManager, state_quarantine
from app.state.schemas import (
    ChangelogEntry,
    OperationType,
    ReadConsistency,
    StateClassification,
    StateDomain,
    StateRecord,
)
from app.state.state_machine import StateMachineValidator
from app.state.versions import VersionManager

logger = logging.getLogger("kairo.state.fabric")


class StateFabric:
    """The central unified state fabric managing authoritative ownership, durability, and consistency."""

    def __init__(
        self,
        cache: ScopedStateCache = scoped_cache,
        changelog: StateChangelog = state_changelog,
        invalidator: CacheInvalidator = cache_invalidator,
        quarantine: StateQuarantineManager = state_quarantine,
    ) -> None:
        self.cache = cache
        self.changelog = changelog
        self.invalidator = invalidator
        self.quarantine = quarantine
        # Internal in-memory store for high-performance and test verification
        self._records: dict[str, StateRecord] = {}

    @classmethod
    def _compute_checksum(cls, data: dict[str, Any]) -> str:
        canonical_bytes = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def _get_key(self, domain: StateDomain, resource_type: str, resource_id: str) -> str:
        return f"{domain.value}:{resource_type}:{resource_id}"

    async def create_record(
        self,
        domain: StateDomain,
        resource_type: str,
        resource_id: str,
        data: dict[str, Any],
        calling_service: str,
        user_id: str | None = None,
        project_id: str | None = None,
        actor: str = "system",
        correlation_id: str | None = None,
        classification: StateClassification = StateClassification.AUTHORITATIVE,
        status: str = "ACTIVE",
    ) -> StateRecord:
        """Creates a new state record under strict domain ownership rules."""
        # 1. Enforce domain ownership boundary
        DomainOwnershipRegistry.validate_mutation_authority(domain, calling_service, classification)

        # 2. Check quarantine
        if self.quarantine.is_quarantined(resource_id):
            raise PermissionError(f"Resource '{resource_id}' is currently quarantined and cannot be mutated.")

        key = self._get_key(domain, resource_type, resource_id)
        if key in self._records:
            raise ValueError(f"State record already exists for '{key}'")

        # 3. Compute deterministic checksum
        checksum = self._compute_checksum(data)

        now = datetime.now(UTC)
        record = StateRecord(
            id=f"rec_{uuid.uuid4().hex[:16]}",
            domain=domain,
            resource_type=resource_type,
            resource_id=resource_id,
            version=1,
            classification=classification,
            status=status,
            data=data,
            checksum=checksum,
            owner_domain=domain,
            user_id=user_id,
            project_id=project_id,
            created_at=now,
            updated_at=now,
        )

        self._records[key] = record

        # 4. Record changelog entry
        self.changelog.record_change(
            domain=domain,
            resource_type=resource_type,
            resource_id=resource_id,
            version=1,
            operation=OperationType.CREATE,
            actor=actor,
            service=calling_service,
            correlation_id=correlation_id,
            changes={"initial": data},
        )

        # 5. Populate cache
        cache_key = self.cache.build_scoped_key(domain.value, resource_id, user_id, project_id)
        self.cache.put(cache_key, record.model_dump(), version=1)

        logger.info("State record created: %s v1 (domain=%s, service=%s)", key, domain.value, calling_service)
        return record

    async def get_record(
        self,
        domain: StateDomain,
        resource_type: str,
        resource_id: str,
        consistency: ReadConsistency = ReadConsistency.STRONG,
        request_user_id: str | None = None,
        request_project_id: str | None = None,
    ) -> StateRecord | None:
        """Retrieves a state record respecting consistency mode and security boundaries."""
        key = self._get_key(domain, resource_type, resource_id)

        # 1. Eventual consistency check in cache
        if consistency == ReadConsistency.EVENTUAL:
            cache_key = self.cache.build_scoped_key(domain.value, resource_id, request_user_id, request_project_id)
            cached_data = self.cache.get(cache_key)
            if cached_data:
                record = StateRecord.model_validate(cached_data)
                DomainOwnershipRegistry.validate_security_scope(
                    record.user_id, request_user_id, record.project_id, request_project_id
                )
                return record

        # 2. Authoritative direct read
        record = self._records.get(key)
        if record is None:
            return None

        # 3. Security boundaries
        DomainOwnershipRegistry.validate_security_scope(
            record.user_id, request_user_id, record.project_id, request_project_id
        )

        return record

    async def update_record(
        self,
        domain: StateDomain,
        resource_type: str,
        resource_id: str,
        new_data: dict[str, Any],
        expected_version: int,
        calling_service: str,
        request_user_id: str | None = None,
        request_project_id: str | None = None,
        actor: str = "system",
        correlation_id: str | None = None,
    ) -> StateRecord:
        """Updates an existing authoritative record with optimistic concurrency validation."""
        key = self._get_key(domain, resource_type, resource_id)
        record = self._records.get(key)
        if record is None:
            raise KeyError(f"State record not found: '{key}'")

        # 1. Enforce ownership and security boundaries
        DomainOwnershipRegistry.validate_mutation_authority(domain, calling_service, record.classification)
        DomainOwnershipRegistry.validate_security_scope(
            record.user_id, request_user_id, record.project_id, request_project_id
        )

        # 2. Check quarantine
        if self.quarantine.is_quarantined(resource_id):
            raise PermissionError(f"Resource '{resource_id}' is quarantined and cannot be modified.")

        # 3. Verify optimistic concurrency
        VersionManager.verify_optimistic_concurrency(
            resource=key,
            expected_version=expected_version,
            actual_version=record.version,
            operation="UPDATE",
        )

        # 4. Apply update with strictly monotonic version increment
        new_version = VersionManager.next_version(record.version)
        checksum = self._compute_checksum(new_data)
        now = datetime.now(UTC)

        updated_record = record.model_copy(
            update={
                "version": new_version,
                "data": new_data,
                "checksum": checksum,
                "updated_at": now,
            }
        )
        self._records[key] = updated_record

        # 5. Record changelog
        self.changelog.record_change(
            domain=domain,
            resource_type=resource_type,
            resource_id=resource_id,
            version=new_version,
            operation=OperationType.UPDATE,
            actor=actor,
            service=calling_service,
            correlation_id=correlation_id,
            changes={"diff": new_data},
        )

        # 6. Invalidate caches
        self.invalidator.on_state_updated(domain.value, resource_id, record.user_id, record.project_id)

        logger.info("Updated state record '%s' to v%d", key, new_version)
        return updated_record

    async def transition_record(
        self,
        domain: StateDomain,
        resource_type: str,
        resource_id: str,
        new_status: str,
        expected_version: int,
        calling_service: str,
        request_user_id: str | None = None,
        request_project_id: str | None = None,
        actor: str = "system",
        correlation_id: str | None = None,
    ) -> StateRecord:
        """Transitions state machine status with explicit transition validation."""
        key = self._get_key(domain, resource_type, resource_id)
        record = self._records.get(key)
        if record is None:
            raise KeyError(f"State record not found: '{key}'")

        # 1. Enforce ownership and boundaries
        DomainOwnershipRegistry.validate_mutation_authority(domain, calling_service, record.classification)
        DomainOwnershipRegistry.validate_security_scope(
            record.user_id, request_user_id, record.project_id, request_project_id
        )

        # 2. Validate state machine transition
        StateMachineValidator.validate_transition(resource_type, record.status, new_status)

        # 3. Verify optimistic concurrency
        VersionManager.verify_optimistic_concurrency(
            resource=key,
            expected_version=expected_version,
            actual_version=record.version,
            operation="TRANSITION",
        )

        new_version = VersionManager.next_version(record.version)
        now = datetime.now(UTC)

        transitioned = record.model_copy(
            update={
                "status": new_status.upper(),
                "version": new_version,
                "updated_at": now,
            }
        )
        self._records[key] = transitioned

        # 4. Record changelog
        self.changelog.record_change(
            domain=domain,
            resource_type=resource_type,
            resource_id=resource_id,
            version=new_version,
            operation=OperationType.TRANSITION,
            actor=actor,
            service=calling_service,
            correlation_id=correlation_id,
            changes={"old_status": record.status, "new_status": new_status.upper()},
        )

        # 5. Invalidate caches
        self.invalidator.on_state_updated(domain.value, resource_id, record.user_id, record.project_id)

        logger.info("Transitioned state record '%s' (%s -> %s) v%d", key, record.status, new_status, new_version)
        return transitioned

    async def delete_record(
        self,
        domain: StateDomain,
        resource_type: str,
        resource_id: str,
        calling_service: str,
        request_user_id: str | None = None,
        request_project_id: str | None = None,
        actor: str = "system",
    ) -> bool:
        """Deletes a state record and propagates cache invalidation."""
        key = self._get_key(domain, resource_type, resource_id)
        record = self._records.get(key)
        if record is None:
            return False

        DomainOwnershipRegistry.validate_mutation_authority(domain, calling_service, record.classification)
        DomainOwnershipRegistry.validate_security_scope(
            record.user_id, request_user_id, record.project_id, request_project_id
        )

        del self._records[key]

        # Record delete operation
        self.changelog.record_change(
            domain=domain,
            resource_type=resource_type,
            resource_id=resource_id,
            version=record.version + 1,
            operation=OperationType.DELETE,
            actor=actor,
            service=calling_service,
        )

        # Purge caches
        self.invalidator.on_resource_deleted(domain.value, resource_id, record.user_id, record.project_id)
        return True

    def get_all_records(self) -> list[StateRecord]:
        """Returns all in-memory records (used by reconciler)."""
        return list(self._records.values())

    def clear(self) -> None:
        self._records.clear()
        self.cache.clear()
        self.changelog.clear()
        self.quarantine.clear()


# Global StateFabric singleton instance
state_fabric = StateFabric()
