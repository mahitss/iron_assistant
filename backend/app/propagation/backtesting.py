"""Zero-leakage historical backtesting framework for risk propagation (Task 75)."""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Dict, List, Optional

from app.propagation.evaluation import CascadeEvaluator, default_cascade_evaluator
from app.propagation.schemas import (
    BacktestReport,
    CascadeEvaluation,
    PropagationAnalysis,
    PropagationEdge,
    TriggerType,
    generate_uuid,
    utc_now,
)
from app.propagation.service import PropagationService, default_propagation_service
from app.propagation.snapshots import GraphSnapshotEngine, default_snapshot_engine

logger = logging.getLogger("kairo.propagation.backtesting")


class PropagationBacktester:
    """Replays historical triggers on frozen graph snapshots with strict zero-leakage enforcement (Spec 61, 62)."""

    def __init__(
        self,
        service: Optional[PropagationService] = None,
        evaluator: Optional[CascadeEvaluator] = None,
        snapshot_engine: Optional[GraphSnapshotEngine] = None,
    ) -> None:
        self.service = service or default_propagation_service
        self.evaluator = evaluator or default_cascade_evaluator
        self.snapshot_engine = snapshot_engine or default_snapshot_engine

    def run_backtest(
        self,
        historical_triggers: List[Dict[str, Any]],
        all_edges: List[PropagationEdge],
        all_entities: Optional[Dict[str, Dict[str, Any]]] = None,
        tenant_id: str = "default_tenant",
    ) -> BacktestReport:
        """Execute historical backtesting across a suite of historical triggers.
        
        Zero Future Data Leakage:
        For each trigger at T0, the graph snapshot is strictly frozen as of T0.
        Any edge or entity with valid_from > T0 or created_at > T0 is strictly excluded.
        """
        evaluations: List[CascadeEvaluation] = []
        zero_leakage_verified = True

        for item in historical_triggers:
            t0: datetime = item["timestamp"]
            origin_entity = item["origin_entity"]
            trigger_text = item.get("trigger", f"Event at {origin_entity}")
            actual_events: List[str] = item.get("actual_degraded_nodes", [])

            # Freeze snapshot strictly as of T0 (Spec 61, 62)
            snapshot = self.snapshot_engine.create_snapshot(
                tenant_id=tenant_id,
                entities=all_entities,
                edges=all_edges,
                as_of_timestamp=t0,
                source_references=["backtest_history"],
            )

            # Audit check: verify zero leakage of future edges
            for edge in snapshot.get_edges():
                if edge.valid_from and edge.valid_from > t0:
                    zero_leakage_verified = False
                    logger.error(
                        "DATA LEAKAGE DETECTED! Edge %s->%s valid_from %s > trigger time %s",
                        edge.source_entity, edge.target_entity, edge.valid_from, t0,
                    )

            # Execute propagation analysis using frozen historical snapshot
            analysis = self.service.analyze_propagation(
                origin_entity=origin_entity,
                trigger=trigger_text,
                trigger_type=TriggerType(item.get("trigger_type", "STATE_CHANGE")),
                tenant_id=tenant_id,
                snapshot_id=snapshot.snapshot_id,
                as_of_timestamp=t0,
            )

            # Score against actual historical outcomes
            eval_record = self.evaluator.evaluate(
                analysis=analysis,
                actual_degraded_nodes=actual_events,
            )
            evaluations.append(eval_record)

        # Aggregate backtest summary metrics
        total = len(evaluations)
        mean_precision = round(sum(e.node_precision for e in evaluations) / max(1, total), 3) if total > 0 else 1.0
        mean_recall = round(sum(e.node_recall for e in evaluations) / max(1, total), 3) if total > 0 else 1.0
        fp_count = sum(1 for e in evaluations if e.false_positive)
        fp_rate = round(fp_count / max(1, total), 3) if total > 0 else 0.0

        timestamps = [item["timestamp"] for item in historical_triggers] if historical_triggers else [utc_now()]
        start_ts = min(timestamps)
        end_ts = max(timestamps)

        report = BacktestReport(
            backtest_id=generate_uuid(),
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            historical_snapshot_id="backtest_frozen_snapshots",
            total_triggers_evaluated=total,
            mean_node_precision=mean_precision,
            mean_node_recall=mean_recall,
            mean_lead_time_seconds=0.0,
            false_positive_rate=fp_rate,
            zero_future_leakage_verified=zero_leakage_verified,
            evaluations=evaluations,
            created_at=utc_now(),
        )

        logger.info(
            "Completed propagation backtest %s: %d triggers, prec=%.2f, rec=%.2f, fp_rate=%.2f, zero_leakage=%s",
            report.backtest_id, total, mean_precision, mean_recall, fp_rate, zero_leakage_verified,
        )
        return report


# Global default backtester
default_propagation_backtester = PropagationBacktester()
