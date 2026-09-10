"""Device Model and authorized telemetry integration (Task 54, Prompts #11-#15)."""

from __future__ import annotations

from typing import Any

from app.environment.confidence import compute_confidence_score
from app.environment.nodes import create_environment_node, generate_canonical_id
from app.environment.schemas import DeviceStatus, DeviceType, EnvironmentNode, NodeType, ScopeType
from app.environment.temporal import calculate_freshness


class DeviceModelManager:
    """Manages authorized device representations in the digital twin."""

    @staticmethod
    def create_device_node(
        device_id: str,
        device_type: DeviceType,
        display_name: str,
        hardware_info: dict[str, Any] | None = None,
        device_status: DeviceStatus = DeviceStatus.UNKNOWN,
        scope_id: str | None = None,
        source: str = "kairo_device_manager",
    ) -> EnvironmentNode:
        canonical = generate_canonical_id(NodeType.DEVICE, device_id, scope_id=scope_id)
        meta = {
            "device_type": device_type.value,
            "hardware": hardware_info or {},
            "status": device_status.value,
        }
        confidence = compute_confidence_score(NodeType.DEVICE, source, calculate_freshness(None))
        return create_environment_node(
            node_id=f"dev_{device_id}",
            node_type=NodeType.DEVICE,
            canonical_id=canonical,
            display_name=display_name,
            metadata=meta,
            scope=ScopeType.DEVICE,
            scope_id=scope_id or device_id,
            status=device_status.value,
            provenance={"source": source, "collector": "device_telemetry"},
            confidence=confidence,
        )
