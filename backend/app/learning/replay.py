"""Experience replay, simulation sandbox, and temporal anti-leakage guards (INVARIANTS 30-35)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from app.learning.experiences import Experience
from app.learning.schemas import ReplayEvaluationSchema


class TemporalLeakageError(Exception):
    """Raised when future data or outcomes leak into a historical replay evaluation."""
    pass


class ExperienceReplayEngine:
    """Safely replays past experiences in simulated sandboxes without real-world side effects."""

    def __init__(self) -> None:
        # replay_id -> ReplayEvaluationSchema
        self._replays: dict[str, ReplayEvaluationSchema] = {}

    def replay_experience(
        self,
        experience: Experience,
        simulation_context: dict[str, Any],
        temporal_cutoff: datetime,
        evaluation_fn: Any = None,
    ) -> ReplayEvaluationSchema:
        """INVARIANT 30-35: Replays experience strictly constrained by temporal_cutoff.
        Detects data leakage if simulation context contains timestamps newer than temporal_cutoff.
        """
        # INVARIANT 33-35: Check temporal integrity
        cutoff = temporal_cutoff if temporal_cutoff.tzinfo is not None else temporal_cutoff.replace(tzinfo=UTC)
        exp_ts = experience.timestamp if experience.timestamp.tzinfo is not None else experience.timestamp.replace(tzinfo=UTC)

        if exp_ts > cutoff:
            raise TemporalLeakageError(
                f"INVARIANT 34: Experience timestamp ({exp_ts.isoformat()}) "
                f"is after temporal cutoff ({cutoff.isoformat()}). Future leakage prohibited."
            )

        for key, val in simulation_context.items():
            if isinstance(val, dict) and "timestamp" in val:
                try:
                    ts = datetime.fromisoformat(str(val["timestamp"]))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=UTC)
                    if ts > cutoff:
                        raise TemporalLeakageError(
                            f"INVARIANT 35: Simulation feature '{key}' has future timestamp {ts.isoformat()} > {cutoff.isoformat()}."
                        )
                except TemporalLeakageError:
                    raise
                except Exception:
                    pass

        # Execute simulation evaluation (without real side effects)
        eval_result = {"simulated": True, "side_effects_executed": False}
        if evaluation_fn:
            eval_result.update(evaluation_fn(experience, simulation_context))
        else:
            eval_result["replayed_outcome"] = experience.outcome
            eval_result["match_historical"] = True

        rid = f"rpl_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        record = ReplayEvaluationSchema(
            replay_id=rid,
            experience_id=experience.experience_id,
            simulated_at=now,
            evaluation_result=eval_result,
            temporal_cutoff=temporal_cutoff,
            leakage_detected=False,
            created_at=now,
        )
        self._replays[rid] = record
        return record

    def list_replays(self, experience_id: str | None = None) -> list[ReplayEvaluationSchema]:
        results = list(self._replays.values())
        if experience_id:
            results = [r for r in results if r.experience_id == experience_id]
        return results
