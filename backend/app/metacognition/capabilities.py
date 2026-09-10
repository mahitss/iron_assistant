"""Capability modeling, tool health tracking, degraded states, and dependency discovery."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional

from app.metacognition.schemas import CapabilitySchema, CapabilityState

logger = logging.getLogger(__name__)


class CapabilityHallucinationError(Exception):
    """Raised when an attempt is made to claim or advertise an unregistered capability."""
    pass


class CapabilityManager:
    """Maintains an accurate, unhallucinated model of actual operational capabilities and tool health."""

    DEFAULT_CAPABILITY_MAP = {
        "text_generation": {"tools": [], "services": ["model_router"], "dependencies": ["llm_api"]},
        "reasoning": {"tools": [], "services": ["cognitive_planner"], "dependencies": ["model_router"]},
        "retrieval": {"tools": ["knowledge_search"], "services": ["knowledge_fabric"], "dependencies": ["vector_store"]},
        "web_research": {"tools": ["web_search", "web_fetch"], "services": ["research_engine"], "dependencies": ["internet_access"]},
        "browser_interaction": {"tools": ["browser_navigate", "browser_click"], "services": ["browser_subagent"], "dependencies": ["playwright"]},
        "code_generation": {"tools": [], "services": ["developer_agent"], "dependencies": ["model_router"]},
        "code_execution": {"tools": ["bash", "python_repl"], "services": ["sandbox_runtime"], "dependencies": ["docker"]},
        "file_operations": {"tools": ["read_file", "write_file", "list_dir"], "services": ["filesystem"], "dependencies": ["local_disk"]},
        "voice": {"tools": ["voice_synthesis", "voice_transcription"], "services": ["voice_pipeline"], "dependencies": ["audio_device"]},
        "vision": {"tools": ["image_inspect", "screen_capture"], "services": ["vision_pipeline"], "dependencies": ["multimodal_model"]},
        "computer_control": {"tools": ["mouse_move", "key_press"], "services": ["os_controller"], "dependencies": ["security_approval"]},
        "automation": {"tools": ["workflow_trigger"], "services": ["automation_engine"], "dependencies": ["event_bus"]},
        "scheduling": {"tools": ["cron_scheduler"], "services": ["timer_service"], "dependencies": ["clock"]},
        "communication": {"tools": ["send_email", "send_chat"], "services": ["communication_service"], "dependencies": ["channel_credentials"]},
    }

    def __init__(self) -> None:
        # capability_name -> CapabilitySchema
        self._capabilities: Dict[str, CapabilitySchema] = {}
        # tool_name -> health dict
        self._tool_health: Dict[str, Dict[str, Any]] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        for name, spec in self.DEFAULT_CAPABILITY_MAP.items():
            self._capabilities[name] = CapabilitySchema(
                name=name,
                category="core",
                description=f"System operational capability: {name}",
                state=CapabilityState.AVAILABLE,
                tools=spec["tools"],
                services=spec["services"],
                dependencies=spec["dependencies"],
                confidence=1.0,
            )

    def register_capability(self, capability: CapabilitySchema) -> CapabilitySchema:
        """Explicit registration of verified capability (INVARIANT 6: No hallucinated capabilities)."""
        self._capabilities[capability.name] = capability
        return capability

    def get_capability(self, name: str) -> Optional[CapabilitySchema]:
        return self._capabilities.get(name)

    def list_capabilities(self, state: Optional[CapabilityState] = None) -> List[CapabilitySchema]:
        caps = list(self._capabilities.values())
        if state:
            caps = [c for c in caps if c.state == state.value]
        return caps

    def update_tool_health(self, tool_name: str, is_healthy: bool, error_msg: Optional[str] = None) -> None:
        """INVARIANT 8 & 9: If a tool is failing, mark its parent capability degraded."""
        self._tool_health[tool_name] = {
            "healthy": is_healthy,
            "last_check": datetime.now(UTC).isoformat(),
            "error": error_msg,
        }

        # Check all capabilities dependent on this tool
        for cap in self._capabilities.values():
            if tool_name in cap.tools:
                if not is_healthy:
                    cap.state = CapabilityState.DEGRADED
                    cap.degradation_reason = f"Tool '{tool_name}' degraded: {error_msg or 'health check failure'}"
                    cap.confidence = 0.5
                    # Suggest safe alternatives if available
                    cap.alternatives = [alt for alt in self._capabilities.keys() if alt != cap.name and self._capabilities[alt].state == CapabilityState.AVAILABLE.value]
                else:
                    # Check if all tools for this capability are now healthy
                    all_healthy = all(
                        self._tool_health.get(t, {}).get("healthy", True)
                        for t in cap.tools
                    )
                    if all_healthy and cap.state == CapabilityState.DEGRADED.value:
                        cap.state = CapabilityState.AVAILABLE
                        cap.degradation_reason = None
                        cap.confidence = 1.0

    def check_capability(self, capability_name: str) -> CapabilitySchema:
        """INVARIANT 11: Before planning, verify whether required capability exists and is available."""
        cap = self.get_capability(capability_name)
        if not cap:
            raise CapabilityHallucinationError(
                f"Capability '{capability_name}' does not exist in registered system. Execution blocked."
            )
        return cap

    def reconcile_with_tool_registry(self, registered_tool_names: List[str]) -> None:
        """INVARIANT 6 & 7: Derives tool availability strictly from ToolRegistry."""
        reg_set = set(registered_tool_names)
        for cap in self._capabilities.values():
            if cap.tools:
                missing = [t for t in cap.tools if t not in reg_set]
                if missing:
                    cap.state = CapabilityState.DEGRADED
                    cap.degradation_reason = f"Required tool(s) missing from ToolRegistry: {', '.join(missing)}"
                    cap.confidence = 0.4
