"""Cascade evaluation and outcome verification engine (Task 75)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional, Set

from app.propagation.schemas import (
    CascadeEvaluation,
    PropagationAnalysis,
    generate_uuid,
    utc_now,
)

logger = logging.getLogger("kairo.propagation.evaluation")


class CascadeEvaluator:
    """Evaluates predicted cascades against actual realized events (Spec 59, 60)."""

    def evaluate(
        self,
        analysis: PropagationAnalysis,
        actual_degraded_nodes: List[str],
        actual_event_timestamps: Optional[Dict[str, datetime]] = None,
        actual_impact_severities: Optional[Dict[str, float]] = None,
    ) -> CascadeEvaluation:
        """Score predicted cascade paths against ground-truth outcomes."""
        predicted_nodes: Set[str] = set()
        for d in analysis.direct_effects:
            predicted_nodes.add(d.target_entity)
        for s in analysis.second_order_effects:
            predicted_nodes.add(s.target_entity)
        for c in analysis.cascades:
            predicted_nodes.update(c.nodes[1:])  # Exclude root origin

        actual_set = set(actual_degraded_nodes)

        tp_nodes = predicted_nodes.intersection(actual_set)
        fp_nodes = predicted_nodes - actual_set
        fn_nodes = actual_set - predicted_nodes

        node_precision = round(len(tp_nodes) / max(1, len(predicted_nodes)), 3)
        node_recall = round(len(tp_nodes) / max(1, len(actual_set)), 3)

        # Path precision: checks whether ordered multi-hop chains were confirmed
        confirmed_paths = 0
        total_paths = len(analysis.cascades)
        for c in analysis.cascades:
            # Path confirmed if all or most of its nodes actually degraded
            if len(c.nodes) >= 2:
                matching_nodes = sum(1 for n in c.nodes[1:] if n in actual_set)
                if matching_nodes == len(c.nodes) - 1:
                    confirmed_paths += 1

        path_precision = round(confirmed_paths / max(1, total_paths), 3) if total_paths > 0 else 1.0
        path_recall = node_recall  # Proxy for path recall

        # Timing error
        timing_error_sum = 0.0
        timing_count = 0
        if actual_event_timestamps:
            analysis_start = analysis.analysis_time
            for d in analysis.direct_effects:
                if d.target_entity in actual_event_timestamps:
                    actual_delay = (actual_event_timestamps[d.target_entity] - analysis_start).total_seconds()
                    predicted_delay = d.temporal_delay.expected_delay_seconds
                    timing_error_sum += abs(actual_delay - predicted_delay)
                    timing_count += 1

        timing_error = round(timing_error_sum / max(1, timing_count), 2) if timing_count > 0 else 0.0

        # Impact estimation error
        impact_err_sum = 0.0
        impact_count = 0
        if actual_impact_severities:
            for d in analysis.direct_effects:
                if d.target_entity in actual_impact_severities:
                    pred_sev = d.impact.operational_impact
                    actual_sev = actual_impact_severities[d.target_entity]
                    impact_err_sum += abs(pred_sev - actual_sev)
                    impact_count += 1
        impact_error = round(impact_err_sum / max(1, impact_count), 3) if impact_count > 0 else 0.0

        # False positive cascade: predicted cascades exist but zero actual nodes degraded
        is_false_positive = len(analysis.cascades) > 0 and len(actual_set) == 0

        evaluation = CascadeEvaluation(
            evaluation_id=generate_uuid(),
            propagation_id=analysis.propagation_id,
            target_origin=analysis.origin_entity,
            predicted_nodes=list(predicted_nodes),
            actual_nodes=list(actual_set),
            missed_nodes=list(fn_nodes),
            false_nodes=list(fp_nodes),
            node_precision=node_precision,
            node_recall=node_recall,
            path_precision=path_precision,
            path_recall=path_recall,
            depth_error=abs(analysis.propagation_depth - (len(actual_set) if len(actual_set) > 0 else 0)),
            timing_error_seconds=timing_error,
            impact_estimation_error=impact_error,
            warning_lead_time_seconds=timing_error,
            false_positive=is_false_positive,
            evaluated_at=utc_now(),
        )

        logger.info(
            "Cascade evaluation %s for origin '%s': node_prec=%.2f, node_rec=%.2f, path_prec=%.2f, false_pos=%s",
            evaluation.evaluation_id, analysis.origin_entity, node_precision, node_recall, path_precision, is_false_positive,
        )
        return evaluation


# Global default evaluator
default_cascade_evaluator = CascadeEvaluator()
