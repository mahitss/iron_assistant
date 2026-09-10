"""Verification audit, anti-fabrication guards, and truthfulness checks (INVARIANTS 79-84, 184)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class FalseVerificationClaimError(Exception):
    """Raised when a system component claims an action was verified without empirical proof."""
    pass


class VerificationAuditGuard:
    """Enforces zero false claims of verification, action execution, tool use, browsing, or memory."""

    def __init__(self) -> None:
        # action_id / claim_id -> verification proof dict
        self._verification_proofs: Dict[str, Dict[str, Any]] = {}

    def register_proof(self, target_id: str, proof_type: str, evidence: Dict[str, Any]) -> None:
        self._verification_proofs[target_id] = {
            "proof_type": proof_type,
            "evidence": evidence,
        }

    def assert_action_executed(self, action_name: str, execution_record: Optional[Dict[str, Any]]) -> None:
        """INVARIANT 80: Never claim 'I sent it' or 'I ran it' unless executed and recorded."""
        if not execution_record or not execution_record.get("executed"):
            raise FalseVerificationClaimError(
                f"Action '{action_name}' cannot be reported as executed without verified execution record."
            )

    def assert_verification_performed(self, claim_subject: str, target_id: Optional[str] = None) -> None:
        """INVARIANT 79 & 81: Never claim 'I verified it' or 'I checked X' unless verification actually occurred."""
        if not target_id or target_id not in self._verification_proofs:
            raise FalseVerificationClaimError(
                f"Verification claim for subject '{claim_subject}' is invalid: no verifiable proof exists in telemetry."
            )

    def assert_tool_invoked(self, tool_name: str, invocation_telemetry: Optional[Dict[str, Any]]) -> None:
        """INVARIANT 82 & 83: Never claim tool use or web research when it did not occur."""
        if not invocation_telemetry or not invocation_telemetry.get("invoked"):
            raise FalseVerificationClaimError(
                f"Tool '{tool_name}' cannot be claimed as used without verified invocation telemetry."
            )
