"""Monotonic versioning and optimistic concurrency control (Task 39, Spec 11-14, 174)."""

from datetime import UTC, datetime
from typing import Any

from app.state.schemas import StateConflict


class StateConflictError(Exception):
    """Raised when an optimistic concurrency version mismatch is detected."""

    def __init__(self, conflict: StateConflict) -> None:
        super().__init__(
            f"State conflict on '{conflict.resource}': expected version {conflict.expected_version}, but actual version is {conflict.actual_version}"
        )
        self.conflict = conflict


class VersionManager:
    """Manages monotonic versions and verifies optimistic concurrency."""

    @classmethod
    def next_version(cls, current_version: int) -> int:
        """Returns strictly monotonic next integer version."""
        if current_version < 1:
            return 1
        return current_version + 1

    @classmethod
    def verify_optimistic_concurrency(
        cls,
        resource: str,
        expected_version: int,
        actual_version: int,
        operation: str = "UPDATE",
    ) -> None:
        """Validates that the expected version matches actual current version.
        
        If mismatch:
        Raises StateConflictError preventing lost updates.
        """
        if expected_version != actual_version:
            conflict = StateConflict(
                resource=resource,
                expected_version=expected_version,
                actual_version=actual_version,
                operation=operation,
                timestamp=datetime.now(UTC),
                details="Optimistic concurrency mismatch. Another worker updated the resource concurrently.",
            )
            raise StateConflictError(conflict)

    @classmethod
    def validate_client_version(
        cls,
        client_version: int | None,
        authoritative_version: int,
    ) -> None:
        """Protects against client version forgery.
        
        Clients cannot forge arbitrary future versions (e.g. claiming version 999).
        The server deterministically computes authoritative versions.
        """
        if client_version is not None and client_version > authoritative_version:
            raise ValueError(
                f"Client version forgery detected: client claimed version {client_version}, but authoritative version is {authoritative_version}"
            )
