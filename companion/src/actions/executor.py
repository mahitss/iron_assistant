"""Local Action Executor coordinating the end-to-end command validation, policy, and execution pipeline."""

import logging
from typing import Any

from companion.src.actions.base import BaseCompanionAction
from companion.src.approvals.verifier import ApprovalArtifactVerifier
from companion.src.audio.microphone import AudioRecordAction, MicrophoneManager
from companion.src.audio.speaker import AudioPlayAction, SpeakerManager
from companion.src.camera.capture import CameraCaptureAction, CameraManager
from companion.src.device.identity import DeviceIdentityManager
from companion.src.filesystem.operations import FilesystemAction
from companion.src.filesystem.sandbox import FilesystemSandbox
from companion.src.input.keyboard import KeyboardAction
from companion.src.input.mouse import MouseAction
from companion.src.screen.capture import ScreenCaptureAction, ScreenObserveAction
from companion.src.screen.privacy import ScreenPrivacyManager
from companion.src.security.policy import LocalPolicyEngine
from companion.src.telemetry.logger import LocalAuditLogger
from companion.src.transport.protocol import CommandProtocolValidator

logger = logging.getLogger("kairo.companion.actions.executor")


class LocalActionExecutor:
    """Coordinates command intake, schema validation, policy checks, approval gating, and execution."""

    def __init__(
        self,
        identity_manager: DeviceIdentityManager,
        policy_engine: LocalPolicyEngine,
        approval_verifier: ApprovalArtifactVerifier | None = None,
        audit_logger: LocalAuditLogger | None = None,
        protocol_validator: CommandProtocolValidator | None = None,
        sandbox: FilesystemSandbox | None = None,
    ) -> None:
        self.identity_manager = identity_manager
        self.policy_engine = policy_engine
        self.approval_verifier = approval_verifier or ApprovalArtifactVerifier()
        self.audit_logger = audit_logger or LocalAuditLogger()
        self.protocol_validator = protocol_validator or CommandProtocolValidator()
        self.sandbox = sandbox or FilesystemSandbox(
            allowed_directories=policy_engine.allowed_filesystem_paths
        )

        # Hardware managers
        self.privacy_manager = ScreenPrivacyManager()
        self.mic_manager = MicrophoneManager()
        self.speaker_manager = SpeakerManager()
        self.camera_manager = CameraManager()

        # Action handlers mapping
        self._action_handlers: dict[str, BaseCompanionAction] = {
            "screen.capture": ScreenCaptureAction(self.privacy_manager),
            "screen.observe": ScreenObserveAction(),
            "mouse.move": MouseAction("mouse.move"),
            "mouse.click": MouseAction("mouse.click"),
            "mouse.double_click": MouseAction("mouse.double_click"),
            "mouse.scroll": MouseAction("mouse.scroll"),
            "keyboard.type": KeyboardAction("keyboard.type"),
            "keyboard.press": KeyboardAction("keyboard.press"),
            "audio.record": AudioRecordAction(self.mic_manager),
            "audio.play": AudioPlayAction(self.speaker_manager),
            "camera.capture": CameraCaptureAction(self.camera_manager),
            "filesystem.read": FilesystemAction("filesystem.read", self.sandbox),
            "filesystem.write_restricted": FilesystemAction("filesystem.write_restricted", self.sandbox),
            "filesystem.delete_restricted": FilesystemAction("filesystem.delete_restricted", self.sandbox),
        }

    def execute_command(self, raw_command: dict[str, Any]) -> dict[str, Any]:
        """Process a structured command through the complete defense-in-depth pipeline."""
        target_device_id = self.identity_manager.get_or_create_device_id()
        command_id = str(raw_command.get("command_id", "unknown"))
        action_name = str(raw_command.get("action", "unknown"))

        try:
            # 1. Schema Validation, 30s Expiration, Sequence, and Idempotency Deduplication
            validated = self.protocol_validator.validate_command(
                command=raw_command,
                target_device_id=target_device_id,
            )
            command_id = validated["command_id"]
            action_name = validated["action"]
            parameters = validated["parameters"]
            auth_context = validated["authorization_context"]

            # 2. Action Lookup in Allowlist
            action_handler = self._action_handlers.get(action_name)
            if not action_handler:
                raise KeyError(f"Action '{action_name}' is not in the companion allowlist.")

            # 3. Approval Verification (if authorization_context is provided)
            has_valid_approval = False
            if isinstance(auth_context, dict):
                has_valid_approval, appr_reason = self.approval_verifier.verify_approval(
                    artifact=auth_context,
                    expected_device_id=target_device_id,
                    expected_action=action_name,
                )
                if not has_valid_approval:
                    logger.warning("Approval artifact verification failed: %s", appr_reason)

            # 4. Local Policy Engine Evaluation
            allowed, policy_reason, action_def = self.policy_engine.evaluate_action_request(
                action_name=action_name,
                parameters=parameters,
                has_verified_approval=has_valid_approval,
            )

            if not allowed:
                self.audit_logger.log_event(
                    command_id=command_id,
                    action=action_name,
                    decision="DENIED",
                    success=False,
                    details={"reason": policy_reason},
                )
                return {
                    "command_id": command_id,
                    "action": action_name,
                    "status": "DENIED",
                    "reason": policy_reason,
                    "success": False,
                }

            # 5. Execute Action with Timeout
            timeout = action_def.timeout_seconds if action_def else 5.0
            exec_result = action_handler.execute_with_timeout(parameters, timeout=timeout)

            # 6. Record Audit Event
            success = exec_result.get("success", False)
            self.audit_logger.log_event(
                command_id=command_id,
                action=action_name,
                decision="ALLOWED",
                success=success,
                details=exec_result,
            )

            return {
                "command_id": command_id,
                "action": action_name,
                "status": "COMPLETED" if success else "FAILED",
                "success": success,
                "result": exec_result.get("result"),
                "error": exec_result.get("error"),
            }

        except Exception as exc:
            logger.error("Command '%s' failed: %s", command_id, exc)
            self.audit_logger.log_event(
                command_id=command_id,
                action=action_name,
                decision="ERROR",
                success=False,
                details={"error": str(exc)},
            )
            return {
                "command_id": command_id,
                "action": action_name,
                "status": "ERROR",
                "success": False,
                "error": str(exc),
            }
