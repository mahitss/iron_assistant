"""Unit tests for Rollback Execution, Verification, and Outcome Calibration (Task 62)."""

from app.optimization.calibration import CalibrationTracker
from app.optimization.parameters import AdjustableParameterRegistry
from app.optimization.rollback import RollbackManager
from app.optimization.schemas import ChangeSet, ChangeSetStatus


def test_rollback_execution_and_mandatory_verification():
    """Test Invariant 22, 23: Rollback executed != rollback successful.

    Restoration must be verified against actual registry state.
    """
    registry = AdjustableParameterRegistry()
    manager = RollbackManager(registry=registry)

    # Initial current value of batch_size_items is 10.0
    param = registry.get_parameter("batch_size_items")
    assert param.current_value == 10.0

    # Simulate an active change that increased batch_size_items to 18.0
    registry.apply_value("batch_size_items", 18.0)
    assert registry.get_parameter("batch_size_items").current_value == 18.0

    cs = ChangeSet(
        change_set_id="cs_rollback_01",
        target_parameter="batch_size_items",
        before_state=10.0,
        after_state=18.0,
        reason="Throughput test",
        rollback_strategy="Restore batch_size_items to 10.0",
        status=ChangeSetStatus.APPLYING,
        version=1,
    )

    plan = manager.execute_rollback(cs, reason="Error rate elevated during canary")

    assert plan.is_executed is True
    assert plan.is_verified is True
    assert plan.target_parameter == "batch_size_items"
    assert plan.restoration_value == 10.0
    assert cs.status == ChangeSetStatus.REVERTED
    assert registry.get_parameter("batch_size_items").current_value == 10.0


def test_calibration_tracker_predicted_vs_actual():
    """Test Invariant 25, 26: System learns overconfidence and calibration error without rewriting history."""
    tracker = CalibrationTracker()

    # Accurate prediction: predicted 15%, actual 14%
    rec1 = tracker.record_calibration(
        recommendation_id="rec_01",
        predicted_improvement_pct=15.0,
        actual_improvement_pct=14.0,
        confidence_score=0.90,
    )
    assert rec1.prediction_error == 1.0
    assert rec1.is_overconfident is False

    # Overconfident prediction: predicted 35%, actual 5%
    rec2 = tracker.record_calibration(
        recommendation_id="rec_02",
        predicted_improvement_pct=35.0,
        actual_improvement_pct=5.0,
        confidence_score=0.95,
    )
    assert rec2.prediction_error == 30.0
    assert rec2.is_overconfident is True

    # Average error calculation: (1.0 + 30.0) / 2 = 15.5
    avg_error = tracker.get_average_prediction_error()
    assert avg_error == 15.5

    records = tracker.list_calibration_records()
    assert len(records) == 2
    assert records[0].recommendation_id == "rec_01"
    assert records[1].recommendation_id == "rec_02"
