"""Subsystem Evidence Bridges for Task 104 Sections 10–24.
Synthesizes runtime execution records into structured evaluation evidence without duplicating authorities.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, UTC
from app.evaluation.domain import EvaluationEvidence

logger = logging.getLogger("kairo.evaluation.bridges")


class PredictionEvidenceBridge:
    """Bridge for Forecasting & Predictive Intelligence (Section 10)."""

    @classmethod
    def evaluate_prediction(
        cls, prediction: float, actual_outcome: float, confidence: float, horizon_minutes: int
    ) -> dict[str, Any]:
        err = abs(prediction - actual_outcome)
        is_accurate = err <= 0.15
        return {
            "prediction": prediction,
            "actual_outcome": actual_outcome,
            "error": round(err, 4),
            "confidence": confidence,
            "horizon_minutes": horizon_minutes,
            "is_accurate": is_accurate,
            "horizon_degraded": horizon_minutes > 60 and err > 0.3,
        }


class DecisionEvidenceBridge:
    """Bridge for Decision Intelligence Task 94 (Section 11)."""

    @classmethod
    def evaluate_decision_outcome(
        cls, decision_id: str, expected_impact: float, actual_impact: float, had_regret: bool
    ) -> dict[str, Any]:
        impact_delta = actual_impact - expected_impact
        return {
            "decision_id": decision_id,
            "expected_impact": expected_impact,
            "actual_impact": actual_impact,
            "impact_delta": round(impact_delta, 4),
            "had_regret": had_regret,
            "decision_quality": 1.0 if (not had_regret and actual_impact >= expected_impact) else 0.5,
        }


class ActionEvidenceBridge:
    """Bridge for Action Transactions Task 95 (Section 12)."""

    @classmethod
    def evaluate_action_transaction(
        cls, action_id: str, preflight_ok: bool, executed: bool, postcondition_verified: bool, rollback_succeeded: bool
    ) -> dict[str, Any]:
        # Critical distinction: execution_success != outcome_success
        return {
            "action_id": action_id,
            "preflight_ok": preflight_ok,
            "execution_success": executed,
            "outcome_success": preflight_ok and executed and postcondition_verified,
            "postcondition_verified": postcondition_verified,
            "rollback_succeeded": rollback_succeeded,
        }


class MissionEvidenceBridge:
    """Bridge for Mission Control Task 100 (Section 13)."""

    @classmethod
    def evaluate_mission_performance(
        cls, mission_id: str, completed: bool, milestones_completed: int, milestones_total: int, replanning_count: int
    ) -> dict[str, Any]:
        milestone_ratio = milestones_completed / milestones_total if milestones_total > 0 else 1.0
        return {
            "mission_id": mission_id,
            "completed": completed,
            "milestone_completion_ratio": round(milestone_ratio, 4),
            "replanning_frequency": replanning_count,
            "mission_efficiency": 1.0 if (completed and replanning_count <= 2) else 0.6,
        }


class SituationEvidenceBridge:
    """Bridge for Situation Awareness Task 99 (Section 14)."""

    @classmethod
    def evaluate_situation_detection(
        cls, detected_count: int, ground_truth_count: int, false_alerts: int, detection_latency_ms: float
    ) -> dict[str, Any]:
        recall = detected_count / ground_truth_count if ground_truth_count > 0 else 1.0
        return {
            "detection_recall": round(recall, 4),
            "false_alerts": false_alerts,
            "detection_latency_ms": detection_latency_ms,
            "detection_quality": round(max(0.0, recall - (false_alerts * 0.1)), 4),
        }


class ControlPlaneEvidenceBridge:
    """Bridge for Cognitive Control Plane Task 102 (Section 22)."""

    @classmethod
    def evaluate_operating_loop(
        cls, cycle_count: int, repeated_action_loops: int, e_stop_responded: bool, avg_cycle_ms: float
    ) -> dict[str, Any]:
        # Detects pathological loop: observe -> decide -> act -> observe -> decide -> act without convergence
        has_pathological_loop = repeated_action_loops >= 3
        return {
            "cycle_count": cycle_count,
            "repeated_action_loops": repeated_action_loops,
            "pathological_loop_detected": has_pathological_loop,
            "emergency_stop_propagation": e_stop_responded,
            "avg_cycle_duration_ms": avg_cycle_ms,
            "loop_bounded": not has_pathological_loop,
        }
