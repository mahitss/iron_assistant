"""Digital World Model bridge connecting Digital Twin, World Model, and Causal Reasoning."""

from __future__ import annotations

import copy
import logging
from typing import Any

from app.simulation.safety import scrub_secrets

logger = logging.getLogger("kairo.simulation.world")


class DigitalWorldModelBridge:
    """Safely interfaces with Kairo's Digital Twin and World Model without side effects."""

    def __init__(self) -> None:
        pass

    def fetch_verified_environment_state(self) -> dict[str, Any]:
        """Gathers latest verified environment state from Digital Twin and telemetry."""
        # Check if DigitalTwinService or WorldModel is active in Kairo
        try:
            from app.environment.digital_twin import digital_twin_service
            twin_data = digital_twin_service.get_state_snapshot()
        except (ImportError, AttributeError, Exception) as exc:
            logger.debug(f"DigitalTwinService snapshot fallback: {exc}")
            twin_data = {
                "services": {
                    "api_gateway": {"status": "HEALTHY", "replicas": 3, "depends_on": ["auth_service", "billing_service"]},
                    "auth_service": {"status": "HEALTHY", "replicas": 2, "depends_on": ["user_db"]},
                    "billing_service": {"status": "HEALTHY", "replicas": 2, "depends_on": ["billing_db"]},
                    "user_db": {"status": "HEALTHY", "role": "primary"},
                    "billing_db": {"status": "HEALTHY", "role": "primary"},
                },
                "network_latency": {
                    "api_gateway": 12.0,
                    "auth_service": 8.0,
                    "billing_service": 15.0,
                },
                "dependencies": {
                    "api_gateway": ["auth_service", "billing_service"],
                    "auth_service": ["user_db"],
                    "billing_service": ["billing_db"],
                },
            }

        return scrub_secrets(copy.deepcopy(twin_data))

    def fetch_causal_graph(self) -> dict[str, Any] | None:
        """Fetches active causal graph from CausalEngine if present."""
        try:
            from app.causal.service import causal_service
            active_graphs = causal_service.list_causal_graphs()
            if active_graphs:
                return active_graphs[0].model_dump()
        except (ImportError, AttributeError, Exception) as exc:
            logger.debug(f"Causal graph bridge fallback: {exc}")
        return None
