"""Bounded mouse operations constrained to validated screen coordinates."""

import logging
from typing import Any

from companion.src.actions.base import BaseCompanionAction

logger = logging.getLogger("kairo.companion.input.mouse")


class MouseAction(BaseCompanionAction):
    """Executes validated mouse move, click, double click, and scroll operations."""

    MAX_X = 7680  # Max multi-monitor 8K boundary
    MAX_Y = 4320

    def __init__(self, action_type: str = "mouse.click") -> None:
        super().__init__(name=action_type, default_timeout_seconds=3.0)
        self.action_type = action_type

    def _validate_coords(self, x: Any, y: Any) -> tuple[int, int]:
        """Validate that coordinates are integers within physical display boundaries."""
        try:
            ix, iy = int(x), int(y)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Mouse coordinates must be integers, got ({x}, {y})") from exc

        if not (0 <= ix <= self.MAX_X and 0 <= iy <= self.MAX_Y):
            raise ValueError(
                f"Coordinates ({ix}, {iy}) exceed display boundaries [0..{self.MAX_X}, 0..{self.MAX_Y}]."
            )
        return ix, iy

    def run(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Simulate mouse action safely within bounds."""
        if self.action_type in ("mouse.move", "mouse.click", "mouse.double_click"):
            x, y = self._validate_coords(parameters.get("x", 0), parameters.get("y", 0))
            button = parameters.get("button", "left").lower()
            if button not in ("left", "right", "middle"):
                raise ValueError(f"Invalid mouse button: {button}")

            logger.info("[MOUSE] %s at (%d, %d) [button=%s]", self.action_type, x, y, button)
            return {"action": self.action_type, "x": x, "y": y, "button": button, "executed": True}

        elif self.action_type == "mouse.scroll":
            delta_y = int(parameters.get("delta_y", 0))
            delta_x = int(parameters.get("delta_x", 0))
            logger.info("[MOUSE] scroll delta_x=%d, delta_y=%d", delta_x, delta_y)
            return {"action": "mouse.scroll", "delta_x": delta_x, "delta_y": delta_y, "executed": True}

        raise NotImplementedError(f"Unsupported mouse action type: {self.action_type}")
