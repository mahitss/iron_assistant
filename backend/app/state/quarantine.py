"""State quarantine manager for isolating corrupt projections and bad records (Task 39, Spec 138-140)."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("kairo.state.quarantine")


class QuarantinedItem:
    def __init__(
        self,
        id: str,
        resource_type: str,
        resource_id: str,
        reason: str,
        quarantined_by: str,
        quarantined_at: datetime,
    ) -> None:
        self.id = id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.reason = reason
        self.quarantined_by = quarantined_by
        self.quarantined_at = quarantined_at
        self.released_at: datetime | None = None
        self.released_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "reason": self.reason,
            "quarantined_by": self.quarantined_by,
            "quarantined_at": self.quarantined_at.isoformat(),
            "released_at": self.released_at.isoformat() if self.released_at else None,
            "released_by": self.released_by,
        }


class StateQuarantineManager:
    """Manages isolation of corrupt derived projections and invalid states."""

    def __init__(self) -> None:
        self._quarantined: dict[str, QuarantinedItem] = {}

    def quarantine(
        self,
        resource_type: str,
        resource_id: str,
        reason: str,
        quarantined_by: str = "system",
    ) -> QuarantinedItem:
        """Isolates a corrupt resource in quarantine."""
        item_id = f"qrn_{uuid.uuid4().hex[:16]}"
        item = QuarantinedItem(
            id=item_id,
            resource_type=resource_type,
            resource_id=resource_id,
            reason=reason,
            quarantined_by=quarantined_by,
            quarantined_at=datetime.now(UTC),
        )
        self._quarantined[resource_id] = item
        logger.warning(
            "QUARANTINED resource %s:%s - reason: %s",
            resource_type,
            resource_id,
            reason,
        )
        return item

    def is_quarantined(self, resource_id: str) -> bool:
        """Checks if a resource is actively quarantined."""
        item = self._quarantined.get(resource_id)
        return item is not None and item.released_at is None

    def release(self, resource_id: str, released_by: str = "operator") -> bool:
        """Releases an item from quarantine after remediation."""
        item = self._quarantined.get(resource_id)
        if item and item.released_at is None:
            item.released_at = datetime.now(UTC)
            item.released_by = released_by
            logger.info("RELEASED resource %s from quarantine by %s", resource_id, released_by)
            return True
        return False

    def list_active(self) -> list[QuarantinedItem]:
        """Lists all actively quarantined resources."""
        return [item for item in self._quarantined.values() if item.released_at is None]

    def clear(self) -> None:
        self._quarantined.clear()


# Global quarantine manager instance
state_quarantine = StateQuarantineManager()
