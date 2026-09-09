"""Local risk level classification for companion actions."""

from enum import Enum


class RiskLevel(str, Enum):
    """Action risk classification tiers."""

    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    HIGH_RISK = "HIGH_RISK"
    DESTRUCTIVE = "DESTRUCTIVE"


# Explicit local risk mapping. Cloud is forbidden from downgrading risk!
ACTION_RISK_MAP: dict[str, RiskLevel] = {
    # Screen
    "screen.capture": RiskLevel.READ_ONLY,
    "screen.observe": RiskLevel.READ_ONLY,
    # Mouse
    "mouse.move": RiskLevel.LOW_RISK,
    "mouse.click": RiskLevel.HIGH_RISK,
    "mouse.double_click": RiskLevel.HIGH_RISK,
    "mouse.scroll": RiskLevel.LOW_RISK,
    # Keyboard
    "keyboard.type": RiskLevel.HIGH_RISK,
    "keyboard.press": RiskLevel.HIGH_RISK,
    # Audio
    "audio.record": RiskLevel.LOW_RISK,
    "audio.play": RiskLevel.READ_ONLY,
    # Camera
    "camera.capture": RiskLevel.HIGH_RISK,
    # Filesystem
    "filesystem.read": RiskLevel.READ_ONLY,
    "filesystem.write_restricted": RiskLevel.HIGH_RISK,
    "filesystem.delete_restricted": RiskLevel.DESTRUCTIVE,
}


def get_action_risk(action: str) -> RiskLevel:
    """Retrieve immutable risk level for a companion action."""
    return ACTION_RISK_MAP.get(action, RiskLevel.DESTRUCTIVE)
