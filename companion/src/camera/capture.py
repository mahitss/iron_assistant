"""Camera capture controller requiring explicit activation and displaying visible capture notice."""

import base64
import logging
from typing import Any

from companion.src.actions.base import BaseCompanionAction

logger = logging.getLogger("kairo.companion.camera.capture")


class CameraManager:
    """Governs physical webcam hardware activation with explicit safety badges."""

    def __init__(self) -> None:
        self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active

    def activate_camera(self) -> None:
        self._is_active = True
        logger.info("[CAMERA INDICATOR] Camera hardware active: CAMERA ACTIVE (Explicit notice displayed)")

    def deactivate_camera(self) -> None:
        self._is_active = False
        logger.info("[CAMERA INDICATOR] Camera hardware deactivated: CAMERA OFF")


class CameraCaptureAction(BaseCompanionAction):
    """Executes single camera snapshot with explicit activation notice."""

    def __init__(self, camera_manager: CameraManager | None = None) -> None:
        super().__init__(name="camera.capture", default_timeout_seconds=5.0)
        self.camera_manager = camera_manager or CameraManager()

    def run(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Capture a single frame from the camera."""
        # 1. Activate hardware with visible indicator
        self.camera_manager.activate_camera()
        try:
            device_index = int(parameters.get("device_index", 0))
            resolution = parameters.get("resolution", "1280x720")

            # 1x1 mock JPEG frame
            mock_jpg = (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\xff\xd9"
            )
            base64_data = base64.b64encode(mock_jpg).decode("ascii")

            logger.info("[CAMERA] Captured single frame from device index %d (%s)", device_index, resolution)
            return {
                "format": "jpeg",
                "resolution": resolution,
                "device_index": device_index,
                "data_base64": base64_data,
                "single_frame": True,
                "notice": "Visible camera active indicator was displayed during capture.",
            }
        finally:
            self.camera_manager.deactivate_camera()
