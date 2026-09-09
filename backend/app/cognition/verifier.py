"""Independent verification engine, pre/postcondition validation, and invariant enforcement for Kairo Cognitive Planning (Task 41).

Core Invariant (Spec 75):
Model self-attestation (e.g. the LLM saying 'done' or 'I have completed this') is strictly REJECTED as verification.
Every meaningful step requires empirical, testable, or state-based verification.
"""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.cognition.steps import PlanStep, VerificationSpec


class InvariantViolationError(RuntimeError):
    """Raised when an immutable system or safety invariant is breached."""
    pass


class StepVerificationResult(BaseModel):
    """Authoritative outcome of verifying a step's execution."""

    model_config = ConfigDict(extra="ignore")

    step_id: str
    verified: bool
    check_type: str
    preconditions_satisfied: bool = True
    postconditions_satisfied: bool = True
    invariant_breached: bool = False
    evidence: str
    failure_reason: str | None = None


class CognitiveVerifier:
    """Evaluates step preconditions, postconditions, health probes, and safety invariants."""

    @classmethod
    def verify_preconditions(
        cls,
        step: PlanStep,
        current_state: dict[str, Any],
    ) -> tuple[bool, str]:
        """Validate all preconditions before allowing a step to run."""
        spec = step.verification
        if not spec.preconditions:
            return True, "No explicit preconditions specified."

        for precondition in spec.preconditions:
            pre_lower = precondition.lower()
            # Empirical state checks
            if "writable" in pre_lower and current_state.get("filesystem_readonly") is True:
                return False, f"Precondition failed: {precondition} (filesystem is read-only)"
            if "online" in pre_lower and current_state.get("is_online") is False:
                return False, f"Precondition failed: {precondition} (system is offline)"
            if "exists" in pre_lower and current_state.get("target_exists") is False:
                return False, f"Precondition failed: {precondition} (target resource does not exist)"

        return True, "All step preconditions verified against authoritative state."

    @classmethod
    def verify_postconditions(
        cls,
        step: PlanStep,
        output_result: dict[str, Any] | None,
        current_state: dict[str, Any],
    ) -> StepVerificationResult:
        """Independently verify step outcome after execution. Rejects self-attestation."""
        spec = step.verification
        result = StepVerificationResult(
            step_id=step.step_id,
            verified=True,
            check_type=spec.check_type,
            evidence="Step outcome verified against criteria.",
        )

        output = output_result or {}

        # 1. Anti Self-Attestation Invariant (Spec 75)
        # If output is purely raw text asserting completion without structured data
        if output.get("self_attestation") is True or (isinstance(output.get("message"), str) and output.get("message").lower().strip() in {"done", "completed", "fixed"} and len(output) == 1):
            result.verified = False
            result.postconditions_satisfied = False
            result.failure_reason = "Model self-attestation ('done') rejected as verification."
            result.evidence = "Output consists solely of self-attestation without verifiable data or state evidence."
            return result

        # 2. Invariant Check (Spec 78, 79)
        for invariant in spec.invariants:
            inv_lower = invariant.lower()
            if "available" in inv_lower or "operational" in inv_lower:
                if current_state.get("system_healthy") is False:
                    result.verified = False
                    result.invariant_breached = True
                    result.failure_reason = f"Critical invariant breached: {invariant}"
                    result.evidence = "Authoritative health probe reports unhealthiness."
                    raise InvariantViolationError(f"STOP: Critical invariant violated during step {step.step_id}: {invariant}")

        # 3. Check specific verification types
        if spec.check_type == "OUTPUT_MATCH":
            if spec.target and spec.target in output:
                actual_val = output[spec.target]
                if spec.expected is not None and actual_val != spec.expected:
                    result.verified = False
                    result.postconditions_satisfied = False
                    result.failure_reason = f"Target '{spec.target}' expected '{spec.expected}', observed '{actual_val}'"
                    result.evidence = f"Output key '{spec.target}' mismatch."
            elif spec.expected is not None:
                # Target not in output
                result.verified = False
                result.postconditions_satisfied = False
                result.failure_reason = f"Required verification key '{spec.target}' not present in step output."

        elif spec.check_type == "HEALTH_CHECK":
            endpoint = spec.target or "/health/ready"
            health_status = current_state.get("health_probes", {}).get(endpoint, "healthy")
            if spec.expected and health_status != spec.expected:
                result.verified = False
                result.postconditions_satisfied = False
                result.failure_reason = f"Health check on '{endpoint}' returned '{health_status}', expected '{spec.expected}'"

        elif spec.check_type == "DIFF_CHECK":
            diff = output.get("diff") or current_state.get("git_diff", "")
            if not diff or len(diff.strip()) == 0:
                result.verified = False
                result.postconditions_satisfied = False
                result.failure_reason = "Diff verification failed: no modifications observed in target repository."

        elif spec.check_type == "STATE_CHECK":
            target_key = spec.target
            if target_key and target_key in current_state:
                if spec.expected is not None and current_state[target_key] != spec.expected:
                    result.verified = False
                    result.postconditions_satisfied = False
                    result.failure_reason = f"State attribute '{target_key}' expected '{spec.expected}', found '{current_state[target_key]}'"

        return result
