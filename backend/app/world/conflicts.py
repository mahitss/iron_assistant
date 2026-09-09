"""Conflict detection and resolution engine for Kairo World Model (Task 32, Spec 34, 35, 60, 96, 126)."""

from datetime import UTC, datetime
from enum import Enum
import logging
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.world.entities import WorldEntitySchema
from app.world.registry import SourceAuthority, SourceOfTruthRegistry

logger = logging.getLogger("kairo.world.conflicts")


class ConflictType(str, Enum):
    """Categorization of detected state inconsistencies (Spec 34)."""

    STALE_UPDATE = "STALE_UPDATE"                   # Incoming event has older timestamp or version
    CONTRADICTORY_STATE = "CONTRADICTORY_STATE"     # Two updates claim incompatible states
    VERSION_MISMATCH = "VERSION_MISMATCH"           # State version regression
    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"     # Non-authoritative source attempting overwrite
    DELETED_ENTITY = "DELETED_ENTITY"               # Source reported deleted, entity still active in model


class ConflictResolutionAction(str, Enum):
    """Action taken to resolve a conflict (Spec 35, 60)."""

    REJECT_UPDATE = "REJECT_UPDATE"                 # Stale or unauthorized update discarded
    APPLY_AUTHORITATIVE = "APPLY_AUTHORITATIVE"     # Authoritative source wins, state updated
    TRIGGER_REFRESH = "TRIGGER_REFRESH"             # Authoritative source queried to reconcile truth
    MARK_STALE = "MARK_STALE"                       # Ambiguous conflict marks entity as STALE


class ConflictRecord(BaseModel):
    """Reconciliation audit log entry for state conflicts (Spec 126)."""

    id: str
    entity_id: str
    conflict_type: ConflictType
    current_state: str
    incoming_state: str
    current_source: str
    incoming_source: str
    resolution: ConflictResolutionAction
    details: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StateConflictEngine:
    """Detects and resolves conflicts adhering to authoritative source primacy."""

    @classmethod
    def evaluate_conflict(
        cls,
        existing_entity: WorldEntitySchema,
        new_state: str,
        new_version: Optional[int],
        new_source: str,
        new_observed_at: datetime,
        new_authority: SourceAuthority,
    ) -> Optional[Tuple[ConflictType, ConflictResolutionAction, str]]:
        """
        Evaluate if an update causes a conflict.
        Returns: None if clean update, or (ConflictType, ResolutionAction, Reason)
        """
        # 1. Check version regression (Spec 87)
        if existing_entity.state_version is not None and new_version is not None:
            if new_version < existing_entity.state_version:
                return (
                    ConflictType.VERSION_MISMATCH,
                    ConflictResolutionAction.REJECT_UPDATE,
                    f"Incoming version {new_version} is older than current version {existing_entity.state_version}.",
                )

        # 2. Check timestamp regression (Spec 88)
        if new_observed_at < existing_entity.observed_at:
            return (
                ConflictType.STALE_UPDATE,
                ConflictResolutionAction.REJECT_UPDATE,
                f"Incoming observation at {new_observed_at.isoformat()} is older than current observation at {existing_entity.observed_at.isoformat()}.",
            )

        # 3. Check authority priority (Spec 33)
        is_incoming_authoritative = SourceOfTruthRegistry.is_source_authoritative(
            existing_entity.type, new_source, "state"
        )
        is_existing_authoritative = SourceOfTruthRegistry.is_source_authoritative(
            existing_entity.type, existing_entity.source, "state"
        )

        if is_existing_authoritative and not is_incoming_authoritative:
            if new_state.upper() != existing_entity.state.upper():
                return (
                    ConflictType.UNAUTHORIZED_SOURCE,
                    ConflictResolutionAction.REJECT_UPDATE,
                    f"Non-authoritative source '{new_source}' cannot overwrite authoritative state from '{existing_entity.source}'.",
                )

        # 4. Check contradictory state from authoritative source
        if new_state.upper() != existing_entity.state.upper():
            if is_incoming_authoritative:
                return (
                    ConflictType.CONTRADICTORY_STATE,
                    ConflictResolutionAction.APPLY_AUTHORITATIVE,
                    f"Authoritative source '{new_source}' updated state from '{existing_entity.state}' to '{new_state}'.",
                )

        return None
