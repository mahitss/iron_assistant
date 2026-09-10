"""System limitation modeling, detection, and transparent user explanations (INVARIANTS 14-17, 174)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional
import uuid

from app.metacognition.schemas import (
    LimitationCategory,
    LimitationSeverity,
    LimitationStatus,
    SystemLimitationSchema,
)


class LimitationDetector:
    """Detects and registers operational limitations across knowledge, tools, permissions, and resources."""

    def __init__(self) -> None:
        # limitation_id -> SystemLimitationSchema
        self._limitations: Dict[str, SystemLimitationSchema] = {}

    def register_limitation(
        self,
        category: LimitationCategory,
        description: str,
        scope: str = "GLOBAL",
        severity: LimitationSeverity = LimitationSeverity.MEDIUM,
        source: str = "SYSTEM",
        mitigation_suggestion: Optional[str] = None,
    ) -> SystemLimitationSchema:
        """Records an active operational limitation."""
        lid = str(uuid.uuid4())
        lim = SystemLimitationSchema(
            limitation_id=lid,
            category=category,
            description=description.strip(),
            scope=scope,
            severity=severity,
            source=source,
            status=LimitationStatus.ACTIVE,
            mitigation_suggestion=mitigation_suggestion,
            detected_at=datetime.now(UTC),
        )
        self._limitations[lid] = lim
        return lim

    def resolve_limitation(self, limitation_id: str) -> SystemLimitationSchema:
        """Marks an active limitation as resolved."""
        lim = self._limitations.get(limitation_id)
        if not lim:
            raise ValueError(f"Limitation '{limitation_id}' not found.")
        lim.status = LimitationStatus.RESOLVED
        lim.resolved_at = datetime.now(UTC)
        return lim

    def list_active_limitations(self, category: Optional[LimitationCategory] = None) -> List[SystemLimitationSchema]:
        active = [l for l in self._limitations.values() if l.status == LimitationStatus.ACTIVE.value]
        if category:
            active = [l for l in active if l.category == category.value]
        return active

    def detect_environment_limitations(self, tool_health: Dict[str, Any], network_available: bool = True) -> List[SystemLimitationSchema]:
        """Scans environmental state for new limitations."""
        new_limitations = []

        if not network_available:
            lim = self.register_limitation(
                category=LimitationCategory.NETWORK,
                description="Network connectivity is unavailable; external web research and API requests are disabled.",
                severity=LimitationSeverity.BLOCKING,
                mitigation_suggestion="Check network interface or use local cached knowledge.",
            )
            new_limitations.append(lim)

        for tool_name, health in tool_health.items():
            if not health.get("healthy", True):
                lim = self.register_limitation(
                    category=LimitationCategory.TOOL,
                    description=f"Tool '{tool_name}' is degraded or failing: {health.get('error', 'unknown error')}",
                    severity=LimitationSeverity.HIGH,
                    mitigation_suggestion=f"Restart or reinstall tool service '{tool_name}'.",
                )
                new_limitations.append(lim)

        return new_limitations

    def explain_limitation(self, limitation_id: str) -> Dict[str, Any]:
        """INVARIANT 17 & 174: Transparent, actionable explanation for the user."""
        lim = self._limitations.get(limitation_id)
        if not lim:
            return {"error": f"Limitation '{limitation_id}' not found."}

        return {
            "limitation_id": lim.limitation_id,
            "category": lim.category,
            "description": lim.description,
            "severity": lim.severity,
            "suggested_action": lim.mitigation_suggestion or "Contact administrator or provide required inputs/permissions.",
            "detected_at": lim.detected_at.isoformat(),
        }
