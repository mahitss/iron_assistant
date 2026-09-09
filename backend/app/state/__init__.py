"""Kairo Unified Data & State Fabric (Task 39)."""

from app.state.cache import scoped_cache
from app.state.changelog import state_changelog
from app.state.drift import DriftDetector
from app.state.fabric import state_fabric
from app.state.invalidation import cache_invalidator
from app.state.locks import state_lock_manager
from app.state.ownership import DomainOwnershipRegistry
from app.state.quarantine import state_quarantine
from app.state.rebuild import rebuild_coordinator
from app.state.reconciliation import state_reconciler
from app.state.router import router as state_router
from app.state.schemas import (
    ChangelogEntry,
    DriftSeverity,
    ObservationFreshness,
    OperationType,
    ReadConsistency,
    ReconciliationMode,
    ReconciliationReport,
    StateClassification,
    StateConflict,
    StateDomain,
    StateDrift,
    StateRecord,
    StateSnapshot,
)
from app.state.snapshots import snapshot_manager
from app.state.state_machine import StateMachineValidator
from app.state.versions import StateConflictError, VersionManager

__all__ = [
    "state_fabric",
    "state_router",
    "state_changelog",
    "scoped_cache",
    "cache_invalidator",
    "state_reconciler",
    "snapshot_manager",
    "state_lock_manager",
    "state_quarantine",
    "rebuild_coordinator",
    "DriftDetector",
    "DomainOwnershipRegistry",
    "StateMachineValidator",
    "VersionManager",
    "StateConflictError",
    "StateClassification",
    "StateDomain",
    "ReadConsistency",
    "ReconciliationMode",
    "DriftSeverity",
    "OperationType",
    "ObservationFreshness",
    "StateRecord",
    "StateConflict",
    "StateDrift",
    "StateSnapshot",
    "ChangelogEntry",
    "ReconciliationReport",
]
