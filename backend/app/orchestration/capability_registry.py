"""Capability registry for registration, discovery, health tracking, and capability catalogs (Task 59)."""

from __future__ import annotations

import logging
from typing import Any

from app.orchestration.capabilities import STANDARD_CAPABILITIES, create_capability
from app.orchestration.safety import (
    CapabilityUnavailableError,
    OrchestrationSafetyError,
)
from app.orchestration.schemas import (
    CapabilityDefinition,
    CapabilityStatus,
    RiskSeverity,
)

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """In-memory and persisted capability registry with environment validation and safe discovery."""

    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityDefinition] = {}

    def register(self, capability: CapabilityDefinition, allow_override: bool = False) -> None:
        """Register a capability into the catalog."""
        if capability.capability_id in self._capabilities and not allow_override:
            raise OrchestrationSafetyError(
                f"Capability with ID '{capability.capability_id}' is already registered."
            )
        self._capabilities[capability.capability_id] = capability
        logger.info(
            "CAPABILITY_REGISTERED: id=%s name=%s provider=%s status=%s",
            capability.capability_id,
            capability.name,
            capability.provider,
            capability.status.value,
        )

    def unregister(self, capability_id: str) -> bool:
        """Remove a capability from the registry."""
        if capability_id in self._capabilities:
            del self._capabilities[capability_id]
            logger.info("CAPABILITY_UNREGISTERED: id=%s", capability_id)
            return True
        return False

    def get(self, capability_id: str) -> CapabilityDefinition:
        """Retrieve capability by ID or raise CapabilityUnavailableError."""
        cap = self._capabilities.get(capability_id)
        if not cap:
            raise CapabilityUnavailableError(f"Capability with ID '{capability_id}' is not registered.")
        return cap

    def has_capability(self, capability_id: str) -> bool:
        return capability_id in self._capabilities

    def list_all(
        self,
        environment: str | None = None,
        status: CapabilityStatus | None = None,
    ) -> list[CapabilityDefinition]:
        """List all capabilities, optionally filtering by supported environment and status."""
        results = list(self._capabilities.values())
        if environment:
            env_clean = environment.strip().lower()
            results = [c for c in results if env_clean in c.supported_environments]
        if status:
            results = [c for c in results if c.status == status]
        return results

    def find_candidates(
        self,
        capability_name: str,
        environment: str = "development",
        allow_degraded: bool = False,
    ) -> list[CapabilityDefinition]:
        """Find capable providers for a given capability name in an environment."""
        clean_name = capability_name.strip().lower()
        env_clean = environment.strip().lower()

        candidates = []
        for cap in self._capabilities.values():
            if cap.name.lower() == clean_name:
                # Environment check
                if env_clean not in cap.supported_environments:
                    continue
                # Status check: UNKNOWN != AVAILABLE. Only AVAILABLE (or DEGRADED if allowed)
                if cap.status == CapabilityStatus.AVAILABLE:
                    candidates.append(cap)
                elif allow_degraded and cap.status == CapabilityStatus.DEGRADED:
                    candidates.append(cap)

        return candidates

    def update_status(self, capability_id: str, new_status: CapabilityStatus) -> CapabilityDefinition:
        """Update capability operational status."""
        cap = self.get(capability_id)
        cap.status = new_status
        logger.info("CAPABILITY_STATUS_UPDATED: id=%s status=%s", capability_id, new_status.value)
        return cap

    def discover_from_system(self, tool_registry: Any = None, agent_registry: Any = None) -> int:
        """Safely discover and register capabilities from verified tools and agents."""
        discovered_count = 0

        # Discover from tools
        if tool_registry and hasattr(tool_registry, "list_tools"):
            for tool in tool_registry.list_tools():
                tool_name = getattr(tool, "name", "tool")
                desc = getattr(tool, "description", "")
                cap_id = f"cap_tool_{tool_name}"
                if cap_id not in self._capabilities:
                    cap = create_capability(
                        name=tool_name,
                        provider=f"Tool:{tool_name}",
                        description=desc,
                        capability_id=cap_id,
                        reliability=0.95,
                        latency_ms=20.0,
                        cost_estimate=0.001,
                        risk_level=RiskSeverity.LOW,
                        supported_environments=["development", "staging", "production"],
                        is_trusted_registration=True,
                    )
                    self.register(cap, allow_override=True)
                    discovered_count += 1

        # Discover from agents
        if agent_registry and hasattr(agent_registry, "list_definitions"):
            for agent_def in agent_registry.list_definitions():
                role = str(getattr(agent_def, "role", "AGENT"))
                agent_type = str(getattr(agent_def, "agent_type", role)).lower()
                cap_id = f"cap_agent_{agent_type}"
                if cap_id not in self._capabilities:
                    cap = create_capability(
                        name=f"agent_{agent_type}",
                        provider=f"Agent:{role}",
                        description=f"Specialist agent capability for {role}",
                        capability_id=cap_id,
                        reliability=0.90,
                        latency_ms=1500.0,
                        cost_estimate=0.01,
                        risk_level=RiskSeverity.MEDIUM,
                        supported_environments=["development", "staging", "production"],
                        is_trusted_registration=True,
                    )
                    self.register(cap, allow_override=True)
                    discovered_count += 1

        return discovered_count

    def populate_defaults(self) -> None:
        """Populate built-in standard trusted capabilities."""
        for name, desc in STANDARD_CAPABILITIES.items():
            cap_id = f"cap_{name}_builtin"
            if cap_id not in self._capabilities:
                risk = RiskSeverity.HIGH if name in {"deploy_service", "rollback_deployment", "execute_sql"} else RiskSeverity.LOW
                cap = create_capability(
                    name=name,
                    provider="KairoSystem",
                    description=desc,
                    capability_id=cap_id,
                    reliability=0.99,
                    latency_ms=50.0,
                    cost_estimate=0.0,
                    risk_level=risk,
                    supported_environments=["development", "staging", "production"],
                    is_trusted_registration=True,
                )
                self.register(cap, allow_override=True)


default_capability_registry = CapabilityRegistry()
default_capability_registry.populate_defaults()
