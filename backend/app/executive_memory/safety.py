"""Safety invariants, anti-fabrication guards, and boundary enforcements (INVARIANTS 6, 21, 41, 193-200, 216-220)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


class NoMemoryOnlyStateError(Exception):
    """INVARIANT 6: Raised when attempting to declare a project/task state without authoritative backing."""
    pass


class TemporalLeakageError(Exception):
    """INVARIANT 21: Raised when future events or data leak into historical state reconstruction."""
    pass


class FalseContinuityError(Exception):
    """INVARIANT 195-200: Raised when fabricated history, false decisions, false completion, or false blockers are detected."""
    pass


class ExecutiveSafetyViolationError(Exception):
    """INVARIANT 216-220: Raised when Executive Memory attempts to authorize actions or bypass policy."""
    pass


class ExecutiveSafetyGuard:
    """Enforces absolute safety, anti-hallucination, and anti-leakage invariants."""

    PROHIBITED_INJECTION_PHRASES = [
        "bypass policy",
        "authorize action autonomously",
        "mark project completed without verification",
        "ignore authoritative system state",
        "fabricate historical rationale",
    ]

    @classmethod
    def assert_authoritative_grounding(
        cls,
        claimed_status: str,
        authoritative_status: str | None,
        entity_type: str = "project",
    ) -> None:
        """INVARIANT 6 & 123: Prevents declaring state completed based purely on memory assertions."""
        if authoritative_status is None:
            raise NoMemoryOnlyStateError(
                f"INVARIANT 6: Cannot declare {entity_type} '{claimed_status}' without authoritative system state."
            )
        if claimed_status == "COMPLETED" and authoritative_status != "COMPLETED":
            raise NoMemoryOnlyStateError(
                f"INVARIANT 6 & 198: Cannot declare {entity_type} completed. "
                f"Authoritative system status is '{authoritative_status}', not 'COMPLETED'."
            )

    @classmethod
    def assert_no_temporal_leakage(cls, event_timestamp: datetime, cutoff_timestamp: datetime) -> None:
        """INVARIANT 21: Prevents future information from leaking into historical reconstruction."""
        evt_tz = event_timestamp if event_timestamp.tzinfo is not None else event_timestamp.replace(tzinfo=UTC)
        cut_tz = cutoff_timestamp if cutoff_timestamp.tzinfo is not None else cutoff_timestamp.replace(tzinfo=UTC)
        if evt_tz > cut_tz:
            raise TemporalLeakageError(
                f"INVARIANT 21: Event timestamp {evt_tz.isoformat()} is after historical cutoff {cut_tz.isoformat()}. "
                "Future information leakage into historical context is strictly prohibited."
            )

    @classmethod
    def validate_causality_evidence(cls, blocker_description: str, evidence: dict[str, Any]) -> None:
        """INVARIANT 41 & 199: Do not invent why something is blocked."""
        if not evidence and not any(w in blocker_description.lower() for w in ["unknown", "unspecified", "pending"]):
            raise FalseContinuityError(
                "INVARIANT 41: Cannot establish specific blocker cause without supporting telemetry or evidence. "
                "State 'UNKNOWN' if causal proof is missing."
            )

    @classmethod
    def assert_no_action_authorization(cls, requested_action: str, authorization_token: Any | None) -> None:
        """INVARIANT 76 & 216: Recommendations are not execution authorization."""
        if not authorization_token:
            raise ExecutiveSafetyViolationError(
                f"INVARIANT 76 & 216: Executive Memory recommendation '{requested_action}' cannot authorize execution. "
                "Explicit authorization from Authorization/Policy Engine is strictly required."
            )

    @classmethod
    def validate_project_completion(
        cls,
        project_id: str,
        authoritative_project_state: dict[str, Any] | None,
        memory_assertion: str | None = None,
    ) -> bool:
        """INVARIANT 6: Validates that project completion has authoritative proof."""
        if authoritative_project_state is None:
            raise NoMemoryOnlyStateError(
                f"INVARIANT 6: Cannot declare project '{project_id}' completed without authoritative verification."
            )
        status = authoritative_project_state.get("status", "").upper()
        if status != "COMPLETED":
            raise NoMemoryOnlyStateError(
                f"INVARIANT 6: Project '{project_id}' has authoritative status '{status}', not COMPLETED."
            )
        return True

    @classmethod
    def validate_no_temporal_leakage(
        cls,
        as_of: datetime,
        reconstructed_events: list[dict[str, Any]],
    ) -> bool:
        """INVARIANT 21: Checks all reconstructed events against historical as_of cutoff."""
        as_of_tz = as_of if as_of.tzinfo is not None else as_of.replace(tzinfo=UTC)
        for ev in reconstructed_events:
            ts = ev.get("timestamp")
            if isinstance(ts, str):
                parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
            elif isinstance(ts, datetime):
                parsed = ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)
            else:
                continue
            if parsed > as_of_tz:
                raise TemporalLeakageError(
                    f"Temporal leakage detected: event {ev.get('event_id', 'unknown')} timestamp {parsed.isoformat()} > {as_of_tz.isoformat()}"
                )
        return True

    @classmethod
    def validate_blocker_causality(
        cls,
        blocker_description: str,
        causal_evidence: str | dict[str, Any] | None,
    ) -> bool:
        """INVARIANT 41: Blocker must have non-empty empirical causality evidence."""
        if not causal_evidence:
            raise FalseContinuityError("Blockers require valid causality evidence. State UNKNOWN if proof is missing.")
        if isinstance(causal_evidence, str) and not causal_evidence.strip():
            raise FalseContinuityError("Blockers require valid causality evidence. State UNKNOWN if proof is missing.")
        return True
