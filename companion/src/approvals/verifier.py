"""Approval artifact verifier enforcing cryptographic and scope-bound validation."""

import hashlib
import hmac
import logging
import time
from typing import Any

logger = logging.getLogger("kairo.companion.approvals.verifier")


class ApprovalArtifactVerifier:
    """Verifies that an approval token is valid, matches the target device/action, and is unexpired."""

    def __init__(self, signing_secret: str | bytes | None = None) -> None:
        self.signing_secret = (
            signing_secret.encode("utf-8")
            if isinstance(signing_secret, str)
            else (signing_secret or b"kairo_approval_signing_secret")
        )
        self._used_approvals: set[str] = set()

    def verify_approval(
        self,
        artifact: dict[str, Any],
        expected_device_id: str,
        expected_action: str,
    ) -> tuple[bool, str]:
        """Validate approval artifact integrity, device match, action scope match, and expiration.

        Returns: (is_valid: bool, reason: str)
        """
        required_fields = [
            "approval_id",
            "user_id",
            "device_id",
            "action",
            "target_scope",
            "expires_at",
            "signature",
        ]
        for f in required_fields:
            if f not in artifact:
                return False, f"Missing field '{f}' in approval artifact."

        approval_id = str(artifact["approval_id"])
        device_id = str(artifact["device_id"])
        action = str(artifact["action"])
        target_scope = str(artifact["target_scope"])
        expires_at_str = str(artifact["expires_at"])
        signature = str(artifact["signature"])

        # 1. Check for replay/reuse
        if approval_id in self._used_approvals:
            return (
                False,
                f"Approval artifact '{approval_id}' has already been consumed (single-use constraint).",
            )

        # 2. Match device binding
        if device_id != expected_device_id:
            return (
                False,
                f"Device mismatch: approval is for '{device_id}', current device is '{expected_device_id}'.",
            )

        # 3. Match action scope
        if action != expected_action:
            return (
                False,
                f"Action scope mismatch: approval authorizes '{action}', requested action is '{expected_action}'.",
            )

        # 4. Check expiration
        try:
            # Check ISO or unix timestamp
            import datetime

            if "T" in expires_at_str:
                exp_dt = datetime.datetime.fromisoformat(expires_at_str)
                now_dt = datetime.datetime.now(datetime.timezone.utc)
                if now_dt > exp_dt:
                    return False, f"Approval artifact '{approval_id}' has expired."
            else:
                if time.time() > float(expires_at_str):
                    return False, f"Approval artifact '{approval_id}' has expired."
        except Exception as exc:
            return False, f"Failed to parse approval expiration: {exc}"

        # 5. Verify cryptographic HMAC signature
        signing_content = (
            f"{approval_id}:{artifact['user_id']}:{device_id}:{action}:{target_scope}:{expires_at_str}"
        )
        expected_sig = hmac.new(
            self.signing_secret, signing_content.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return False, "Invalid approval artifact cryptographic signature."

        # Mark single-use approval as consumed
        self._used_approvals.add(approval_id)
        return True, f"Approval '{approval_id}' verified successfully."
