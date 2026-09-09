"""Bounded keyboard actions with sensitive field protection."""

import logging
from typing import Any

from companion.src.actions.base import BaseCompanionAction
from companion.src.input.sensitive import SensitiveContextDetector

logger = logging.getLogger("kairo.companion.input.keyboard")


class KeyboardAction(BaseCompanionAction):
    """Executes validated keyboard typing and keypress simulation."""

    MAX_TEXT_LENGTH = 1000  # Hard limit per command to prevent buffer overflow/freezes

    def __init__(self, action_type: str = "keyboard.type") -> None:
        super().__init__(name=action_type, default_timeout_seconds=5.0)
        self.action_type = action_type

    def run(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute keyboard action after verifying context is not sensitive."""
        target_context = parameters.get("target_context", "")

        if self.action_type == "keyboard.type":
            text = str(parameters.get("text", ""))
            if len(text) > self.MAX_TEXT_LENGTH:
                raise ValueError(
                    f"Text length ({len(text)}) exceeds maximum allowed ({self.MAX_TEXT_LENGTH})."
                )

            # Sensitive Context Check
            is_sensitive, reason = SensitiveContextDetector.is_sensitive_context(
                ui_context=target_context, text_to_type=text
            )
            if is_sensitive:
                raise PermissionError(
                    f"Refusing to type into sensitive context: {reason}. Explicit human interaction required."
                )

            logger.info("[KEYBOARD] Typed %d characters into focus.", len(text))
            return {"action": "keyboard.type", "characters_typed": len(text), "executed": True}

        elif self.action_type == "keyboard.press":
            key = str(parameters.get("key", "")).strip()
            if not key:
                raise ValueError("Key parameter is required for keyboard.press.")

            # Validate key name
            allowed_keys = {
                "enter",
                "return",
                "tab",
                "esc",
                "escape",
                "space",
                "backspace",
                "delete",
                "up",
                "down",
                "left",
                "right",
                "home",
                "end",
                "pageup",
                "pagedown",
                "ctrl",
                "alt",
                "shift",
                "meta",
                "f1",
                "f2",
                "f3",
                "f4",
                "f5",
                "f6",
                "f7",
                "f8",
                "f9",
                "f10",
                "f11",
                "f12",
            }
            if len(key) == 1:
                # Single character key
                pass
            elif key.lower() not in allowed_keys:
                raise ValueError(f"Key '{key}' is not an allowed key.")

            logger.info("[KEYBOARD] Pressed key: %s", key)
            return {"action": "keyboard.press", "key": key, "executed": True}

        raise NotImplementedError(f"Unsupported keyboard action type: {self.action_type}")
