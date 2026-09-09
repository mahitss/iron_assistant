"""Explicit action registry enforcing strict allowlist and hard-blocking arbitrary code execution."""

import logging
from dataclasses import dataclass
from typing import Any

from companion.src.permissions.risk import RiskLevel

logger = logging.getLogger("kairo.companion.permissions.registry")


@dataclass(frozen=True)
class ActionDefinition:
    """Metadata and constraints for an allowlisted companion action."""

    name: str
    description: str
    risk_level: RiskLevel
    capability: str
    requires_approval: bool
    timeout_seconds: float


FORBIDDEN_OPERATIONS = {
    "shell.execute",
    "shell.run",
    "bash.run",
    "powershell.run",
    "cmd.run",
    "arbitrary_python",
    "arbitrary_process",
    "process.spawn",
    "system.reboot",
    "system.shutdown",
    "registry.write",
}


class ActionRegistry:
    """Authoritative local registry of all allowlisted actions callable on this device."""

    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register the safe, bounded V1.1 companion actions."""
        builtins = [
            ActionDefinition(
                name="screen.capture",
                description="Capture a single static screenshot frame of the active display.",
                risk_level=RiskLevel.READ_ONLY,
                capability="computer_control",
                requires_approval=False,
                timeout_seconds=5.0,
            ),
            ActionDefinition(
                name="screen.observe",
                description="Inspect bounding boxes and visible window titles.",
                risk_level=RiskLevel.READ_ONLY,
                capability="computer_control",
                requires_approval=False,
                timeout_seconds=5.0,
            ),
            ActionDefinition(
                name="mouse.move",
                description="Move mouse cursor to specific coordinates (x, y).",
                risk_level=RiskLevel.LOW_RISK,
                capability="computer_control",
                requires_approval=False,
                timeout_seconds=3.0,
            ),
            ActionDefinition(
                name="mouse.click",
                description="Simulate single click at specific coordinates (x, y).",
                risk_level=RiskLevel.HIGH_RISK,
                capability="computer_control",
                requires_approval=True,
                timeout_seconds=3.0,
            ),
            ActionDefinition(
                name="mouse.double_click",
                description="Simulate double click at specific coordinates (x, y).",
                risk_level=RiskLevel.HIGH_RISK,
                capability="computer_control",
                requires_approval=True,
                timeout_seconds=3.0,
            ),
            ActionDefinition(
                name="mouse.scroll",
                description="Scroll active viewport by vertical/horizontal delta.",
                risk_level=RiskLevel.LOW_RISK,
                capability="computer_control",
                requires_approval=False,
                timeout_seconds=3.0,
            ),
            ActionDefinition(
                name="keyboard.type",
                description="Type bounded non-sensitive text into active window focus.",
                risk_level=RiskLevel.HIGH_RISK,
                capability="computer_control",
                requires_approval=True,
                timeout_seconds=5.0,
            ),
            ActionDefinition(
                name="keyboard.press",
                description="Press a specific modifier or function key (e.g. Enter, Esc, Tab).",
                risk_level=RiskLevel.HIGH_RISK,
                capability="computer_control",
                requires_approval=True,
                timeout_seconds=3.0,
            ),
            ActionDefinition(
                name="audio.record",
                description="Record short audio clip from microphone after explicit activation.",
                risk_level=RiskLevel.LOW_RISK,
                capability="microphone",
                requires_approval=False,
                timeout_seconds=10.0,
            ),
            ActionDefinition(
                name="audio.play",
                description="Play TTS audio output through local speaker with stop control.",
                risk_level=RiskLevel.READ_ONLY,
                capability="speaker",
                requires_approval=False,
                timeout_seconds=15.0,
            ),
            ActionDefinition(
                name="camera.capture",
                description="Capture a single camera frame with visible indicator active.",
                risk_level=RiskLevel.HIGH_RISK,
                capability="camera",
                requires_approval=True,
                timeout_seconds=5.0,
            ),
            ActionDefinition(
                name="filesystem.read",
                description="Read file contents within approved workspace allowlist directories.",
                risk_level=RiskLevel.READ_ONLY,
                capability="filesystem",
                requires_approval=False,
                timeout_seconds=5.0,
            ),
            ActionDefinition(
                name="filesystem.write_restricted",
                description="Write or overwrite file strictly inside approved workspace directories.",
                risk_level=RiskLevel.HIGH_RISK,
                capability="filesystem",
                requires_approval=True,
                timeout_seconds=5.0,
            ),
            ActionDefinition(
                name="filesystem.delete_restricted",
                description="Delete file strictly inside approved workspace directories.",
                risk_level=RiskLevel.DESTRUCTIVE,
                capability="filesystem",
                requires_approval=True,
                timeout_seconds=5.0,
            ),
        ]
        for act in builtins:
            self._actions[act.name] = act

    def get_action(self, name: str) -> ActionDefinition:
        """Lookup action definition or reject with security exception."""
        clean_name = name.strip().lower()

        # Hard block forbidden patterns
        if clean_name in FORBIDDEN_OPERATIONS or any(
            p in clean_name for p in ["shell", "exec", "eval", "spawn"]
        ):
            logger.critical("SECURITY ALERT: Forbidden action attempted: '%s'", name)
            raise PermissionError(
                f"Action '{name}' is strictly FORBIDDEN. Arbitrary OS execution is prohibited."
            )

        if clean_name not in self._actions:
            raise KeyError(f"Action '{name}' is not in the companion allowlist.")

        return self._actions[clean_name]

    def list_allowlisted_actions(self) -> list[dict[str, Any]]:
        """Return list of all registered allowlisted actions."""
        return [
            {
                "name": a.name,
                "description": a.description,
                "risk": a.risk_level.value,
                "capability": a.capability,
                "requires_approval": a.requires_approval,
                "timeout_seconds": a.timeout_seconds,
            }
            for a in self._actions.values()
        ]
