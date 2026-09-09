"""Device policy enforcement module for Kairo Governance (Task 36).

Enforces:
- Revoked device blocking (immediate DENY).
- Trusted device requirements for privileged/sensitive operations (trusted != permission).
- Device capability verification (cannot perform actions unsupported by device).
- Reconnect re-evaluation requirements.
"""

from typing import Any

from app.policy.schemas import PolicyContext, PolicyDecisionType, RiskLevel


class DevicePolicyEnforcer:
    """Validates device state, trust level, and capabilities against operation requirements."""

    @classmethod
    def evaluate_device(cls, context: PolicyContext, assessed_risk: RiskLevel) -> tuple[PolicyDecisionType | None, str | None]:
        """Evaluate device posture against requested action and assessed risk.

        Returns (Decision, Reason) if device invariant triggers, else (None, None).
        """
        device = context.device
        action = (context.action or "").strip().lower()
        tool = str(context.tool or "")

        # If no device context is supplied, but the action is a local hardware/computer control action:
        is_hardware_action = (
            action.startswith("computer_") or tool.startswith("computer_") or
            any(k in action for k in ("screen_read", "microphone", "camera", "mouse", "keyboard"))
        )
        if not device and is_hardware_action:
            return PolicyDecisionType.DENY, "Hardware/computer control operation requires an active registered device"

        if not device:
            return None, None

        # 1. Revocation Check (Section 126)
        if device.get("is_revoked") is True or device.get("status") == "revoked":
            return PolicyDecisionType.DENY, f"Device '{device.get('id', 'unknown')}' has been revoked. Access denied"

        # 2. Connection state & Freshness (Section 140)
        if device.get("is_connected") is False or device.get("status") == "disconnected":
            return PolicyDecisionType.DENY, "Device is disconnected. Policy requires active connected device"

        if device.get("reconnected_needs_reeval") is True:
            # Reconnected device must trigger full re-evaluation
            return PolicyDecisionType.DEFER, "Device reconnected during task; state must be re-validated"

        is_trusted = device.get("is_trusted") is True or device.get("trust_level") in ("trusted", "high", "hardware_enclave")

        # 3. Sensitive / High-Risk Operations Require Trusted Device (Sections 18, 64, 125)
        # Privileged computer control, financial, or R3/R4 operations must be from a trusted device
        if assessed_risk in (RiskLevel.R3_HIGH, RiskLevel.R4_CRITICAL) or is_hardware_action:
            if not is_trusted:
                # If untrusted device attempts computer control input or high risk:
                if is_hardware_action and any(k in action or k in tool for k in ("click", "type", "input", "press")):
                    return PolicyDecisionType.REQUIRE_STEP_UP_AUTH, "Privileged computer control from untrusted device requires step-up authentication and device authorization"
                if assessed_risk == RiskLevel.R4_CRITICAL:
                    return PolicyDecisionType.DENY, "Critical operations are prohibited from untrusted devices"

        # 4. Capability verification (Section 65)
        capabilities: list[str] = [c.lower() for c in (device.get("capabilities") or [])]
        if is_hardware_action:
            if "screen" in action or "screenshot" in tool or "screen_read" in action:
                if "screen_capture" not in capabilities and "screen" not in capabilities:
                    return PolicyDecisionType.DENY, f"Device '{device.get('id')}' lacks 'screen_capture' capability"
            if "click" in action or "type" in action or "mouse" in tool or "keyboard" in tool:
                if "input_injection" not in capabilities and "computer_control" not in capabilities:
                    return PolicyDecisionType.DENY, f"Device '{device.get('id')}' lacks 'input_injection' capability"
            if "microphone" in action or "audio_record" in action:
                if "microphone" not in capabilities and "audio_capture" not in capabilities:
                    return PolicyDecisionType.DENY, f"Device '{device.get('id')}' lacks 'audio_capture' capability"
            if "camera" in action or "video_record" in action:
                if "camera" not in capabilities and "video_capture" not in capabilities:
                    return PolicyDecisionType.DENY, f"Device '{device.get('id')}' lacks 'video_capture' capability"

        return None, None
