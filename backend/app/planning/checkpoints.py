"""Strategic checkpoints, expected vs actual state comparison, and stopping rules (Task 58)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.planning.schemas import PlanCheckpoint

logger = logging.getLogger(__name__)


class CheckpointEngine:
    """Evaluates checkpoints against actual observed reality and triggers stopping rules."""

    def evaluate_checkpoint(
        self,
        checkpoint: PlanCheckpoint,
        observed_state: dict[str, Any],
    ) -> PlanCheckpoint:
        """Compare expected state vs observed state and determine stopping rule."""
        checkpoint.observed_state = observed_state
        checkpoint.evaluated_at = datetime.now(timezone.utc)

        expected = checkpoint.expected_state or {}
        if not expected:
            checkpoint.variance_score = 0.0
            checkpoint.decision_action = "CONTINUE"
            return checkpoint

        total_keys = len(expected)
        mismatch_count = 0.0

        for key, exp_val in expected.items():
            obs_val = observed_state.get(key)
            if obs_val is None:
                mismatch_count += 1.0
            elif isinstance(exp_val, (int, float)) and isinstance(obs_val, (int, float)):
                # Relative difference for numeric metrics
                base = max(abs(exp_val), 1.0)
                diff = min(1.0, abs(obs_val - exp_val) / base)
                mismatch_count += diff
            elif obs_val != exp_val:
                mismatch_count += 1.0

        variance = round(min(1.0, mismatch_count / max(1, total_keys)), 2)
        checkpoint.variance_score = variance

        # Stopping Rules (Items 42, 81)
        if variance <= 0.15:
            checkpoint.decision_action = "CONTINUE"
        elif variance <= 0.40:
            checkpoint.decision_action = "PAUSE"
            logger.info("Checkpoint '%s' variance %s warrants PAUSE.", checkpoint.name, variance)
        elif variance <= 0.70:
            checkpoint.decision_action = "REPLAN"
            logger.warning("Checkpoint '%s' variance %s warrants REPLAN.", checkpoint.name, variance)
        else:
            checkpoint.decision_action = "ROLLBACK"
            logger.error("Checkpoint '%s' severe variance %s warrants ROLLBACK.", checkpoint.name, variance)

        return checkpoint


checkpoint_engine = CheckpointEngine()
