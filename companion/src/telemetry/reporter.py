"""Minimal telemetry reporter sending safe health and connection metrics to Kairo Cloud."""

import logging
from typing import Any

from companion.src.device.identity import DeviceIdentityManager
from companion.src.device.state import DeviceStateManager
from companion.src.transport.client import CompanionTransportClient

logger = logging.getLogger("kairo.companion.telemetry.reporter")


class TelemetryReporter:
    """Gathers minimal safe telemetry without exposing user screen, audio, or camera content."""

    def __init__(
        self,
        identity_manager: DeviceIdentityManager,
        state_manager: DeviceStateManager,
        transport_client: CompanionTransportClient,
    ) -> None:
        self.identity_manager = identity_manager
        self.state_manager = state_manager
        self.transport_client = transport_client

    def generate_heartbeat_payload(self) -> dict[str, Any]:
        """Generate safe periodic heartbeat telemetry."""
        info = self.identity_manager.get_device_info()
        status = self.state_manager.get_status_summary()

        payload = {
            "device_id": info["device_id"],
            "companion_version": "1.1.0",
            "os_name": info["os_name"],
            "os_version": info["os_version"],
            "state": status["state"],
            "capabilities": status["capabilities"],
            "session_state": self.transport_client.session_state.value,
            "idle_seconds": status["idle_seconds"],
        }
        return payload
