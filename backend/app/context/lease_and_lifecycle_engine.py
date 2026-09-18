"""Lease and Lifecycle Engine for Task 110:
Governs working set validity leases, event-driven invalidations, and targeted revalidation.

Strict Invariants:
- A working set cannot outlive its validity lease.
- Invalidated context cannot be reused without revalidation.
- EmergencyStop immediately invalidates execution-related working sets fail-closed.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import List, Optional, Tuple

from app.context.working_set_domain import (
    ContextLease,
    LeaseState,
    WorkingSet,
    WorkingSetLifecycle,
    gen_ctx_id,
    utc_now,
)


class LeaseAndLifecycleEngine:
    """Manages short-lived leases and event-driven invalidations for working sets."""

    DEFAULT_LEASE_TTL_SECONDS = 60.0

    @classmethod
    def grant_lease(
        cls,
        working_set_id: str,
        version: int = 1,
        ttl_seconds: float = DEFAULT_LEASE_TTL_SECONDS,
    ) -> ContextLease:
        """Issue a fresh time-bounded validity lease for a working set."""
        now = utc_now()
        expires = now + timedelta(seconds=ttl_seconds)

        return ContextLease(
            lease_id=gen_ctx_id("clease"),
            working_set_id=working_set_id,
            working_set_version=version,
            state=LeaseState.VALID,
            ttl_seconds=ttl_seconds,
            granted_at=now,
            expires_at=expires,
        )

    @classmethod
    def evaluate_lease(cls, lease: ContextLease) -> ContextLease:
        """Check lease expiration against current monotonic time."""
        now = utc_now()
        if lease.state in (LeaseState.INVALIDATED, LeaseState.EXPIRED):
            return lease

        if now >= lease.expires_at:
            lease.state = LeaseState.EXPIRED
            return lease

        remaining = (lease.expires_at - now).total_seconds()
        if remaining < (lease.ttl_seconds * 0.25):
            lease.state = LeaseState.AGING
        else:
            lease.state = LeaseState.VALID

        return lease

    @classmethod
    def invalidate_working_set(
        cls,
        working_set: WorkingSet,
        reason: str = "World state changed or EmergencyStop triggered",
    ) -> WorkingSet:
        """Invalidate a working set and its lease fail-closed."""
        now = utc_now()
        working_set.lifecycle = WorkingSetLifecycle.INVALIDATED
        working_set.updated_at = now

        if working_set.lease:
            working_set.lease.state = LeaseState.INVALIDATED
            working_set.lease.invalidated_at = now
            working_set.lease.invalidation_reason = reason

        return working_set

    @classmethod
    def prepare_revalidation(
        cls,
        working_set: WorkingSet,
        sections_to_refresh: List[str],
        trigger_reason: str,
    ) -> Tuple[WorkingSet, int]:
        """Advance working set version for targeted incremental refresh."""
        old_version = working_set.version
        new_version = old_version + 1

        working_set.version = new_version
        working_set.lifecycle = WorkingSetLifecycle.REFRESHING
        working_set.updated_at = utc_now()

        # Issue refreshed lease for the new version
        working_set.lease = cls.grant_lease(
            working_set_id=working_set.working_set_id,
            version=new_version,
            ttl_seconds=cls.DEFAULT_LEASE_TTL_SECONDS,
        )

        return working_set, new_version
