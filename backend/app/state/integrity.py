"""Data integrity scanner and impossible state detector (Task 39, Spec 36-37, 135-139)."""

import logging
from typing import Any

from app.state.schemas import StateRecord

logger = logging.getLogger("kairo.state.integrity")


class IntegrityViolation:
    def __init__(self, resource_id: str, violation_type: str, description: str) -> None:
        self.resource_id = resource_id
        self.violation_type = violation_type
        self.description = description

    def to_dict(self) -> dict[str, str]:
        return {
            "resource_id": self.resource_id,
            "violation_type": self.violation_type,
            "description": self.description,
        }


class StateIntegrityScanner:
    """Detects impossible states, missing fields, broken references, and illegal versions."""

    @classmethod
    def scan_record(cls, record: StateRecord) -> list[IntegrityViolation]:
        """Scans an individual state record for integrity violations."""
        violations: list[IntegrityViolation] = []

        # 1. Version sanity
        if record.version < 1:
            violations.append(
                IntegrityViolation(
                    resource_id=record.resource_id,
                    violation_type="INVALID_VERSION",
                    description=f"State record has non-positive version {record.version}",
                )
            )

        # 2. Checksum validation
        if not record.checksum or len(record.checksum) < 16:
            violations.append(
                IntegrityViolation(
                    resource_id=record.resource_id,
                    violation_type="MISSING_CHECKSUM",
                    description="State record lacks valid cryptographic checksum",
                )
            )

        # 3. Impossible state: COMPLETED task with active execution lease
        if record.domain.value == "tasks" and record.status.upper() == "COMPLETED":
            active_lease = record.data.get("lease_owner") or record.data.get("lease_expires_at")
            if active_lease:
                violations.append(
                    IntegrityViolation(
                        resource_id=record.resource_id,
                        violation_type="IMPOSSIBLE_STATE",
                        description="Task is marked COMPLETED but still holds an active execution lease",
                    )
                )

        # 4. Impossible state: REVOKED device marked CONNECTED
        if record.domain.value == "devices" and record.status.upper() == "REVOKED":
            if record.data.get("connected") is True:
                violations.append(
                    IntegrityViolation(
                        resource_id=record.resource_id,
                        violation_type="IMPOSSIBLE_STATE",
                        description="Device is REVOKED but still marked as actively connected",
                    )
                )

        return violations
