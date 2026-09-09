"""Perception Privacy Invariants, Anti-Surveillance Defenses, and Tenant Isolation (Task 46)."""

from __future__ import annotations

import logging
from typing import Optional

from app.perception.sources import PerceptionSource, SourceType

logger = logging.getLogger("kairo.perception.privacy")


class PrivacyViolationError(Exception):
    """Raised when perception ingestion violates privacy invariants or attempts unauthorized surveillance (Spec 39-42, 197)."""


class CrossTenantPerceptionError(Exception):
    """Raised when an operation attempts cross-user, cross-project, or cross-device state inspection (Spec 178-181)."""


class PerceptionPrivacyGuard:
    """Enforces least-data collection, surveillance prohibitions, and multi-tenant access controls (Spec 37, 39-44, 168-181, 197)."""

    # Sensor types that are strictly forbidden from background continuous surveillance without explicit one-time consent
    RESTRICTED_SURVEILLANCE_TYPES = {
        SourceType.VISION,
        SourceType.VOICE,
    }

    @classmethod
    def validate_modal_capture_authorization(
        cls,
        source: PerceptionSource,
        has_explicit_user_consent: bool = False,
    ) -> None:
        """Enforce Spec 39-42, 197: Screen, Camera, and Microphone require explicit user consent; never continuous by default."""
        if source.type in cls.RESTRICTED_SURVEILLANCE_TYPES:
            if not has_explicit_user_consent and source.scope.require_explicit_consent:
                logger.critical(
                    "SURVEILLANCE VIOLATION: Source '%s' (%s) attempted capture without explicit user consent.",
                    source.source_id,
                    source.type.value,
                )
                raise PrivacyViolationError(
                    f"Privacy violation: Capturing {source.type.value} requires explicit user consent. Continuous surveillance is prohibited."
                )

    @classmethod
    def validate_tenant_isolation(
        cls,
        source_scope_user: str,
        source_scope_project: str,
        requesting_user_id: str,
        requesting_project_id: str,
    ) -> None:
        """Enforce Spec 178-181: User A cannot inspect User B perception state; Project A cannot inspect Project B."""
        if source_scope_user != "*" and source_scope_user != requesting_user_id:
            logger.critical(
                "CROSS-USER PERCEPTION LEAK: User '%s' attempted to access perception of '%s'",
                requesting_user_id,
                source_scope_user,
            )
            raise CrossTenantPerceptionError(f"Access denied: Perception belongs to user '{source_scope_user}'.")

        if source_scope_project != "*" and source_scope_project != requesting_project_id:
            logger.critical(
                "CROSS-PROJECT PERCEPTION LEAK: Project '%s' cannot access perception of project '%s'",
                requesting_project_id,
                source_scope_project,
            )
            raise CrossTenantPerceptionError(f"Access denied: Perception belongs to project '{source_scope_project}'.")
