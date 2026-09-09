"""Communication metrics, evaluation dimensions, and feedback-driven learning loops."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class CommunicationEvaluator:
    """Tracks operational telemetry, accuracy scores, and user feedback."""

    def __init__(self) -> None:
        self.metrics = {
            "messages_processed": 0,
            "drafts_generated": 0,
            "drafts_approved": 0,
            "drafts_edited": 0,
            "drafts_rejected": 0,
            "sends_attempted": 0,
            "sends_successful": 0,
            "deliveries_verified": 0,
            "followups_scheduled": 0,
            "injections_blocked": 0,
            "secrets_blocked": 0,
        }
        self._user_feedback_log: List[Dict[str, Any]] = []

    def record_metric(self, metric_name: str, increment: int = 1) -> None:
        if metric_name in self.metrics:
            self.metrics[metric_name] += increment

    def record_user_feedback(
        self,
        draft_id: str,
        feedback_type: str,  # approve, edit, reject, regenerate
        original_content: str,
        edited_content: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """INVARIANTS 174 & 175: Record user edits and feedback to guide tone and preference adaptation."""
        record = {
            "draft_id": draft_id,
            "feedback_type": feedback_type,
            "has_edits": bool(edited_content and edited_content != original_content),
            "notes": notes,
        }
        self._user_feedback_log.append(record)

        if feedback_type == "approve":
            self.record_metric("drafts_approved")
        elif feedback_type == "edit":
            self.record_metric("drafts_edited")
        elif feedback_type == "reject":
            self.record_metric("drafts_rejected")

        return record

    def get_summary_metrics(self) -> Dict[str, Any]:
        total_drafts = self.metrics["drafts_generated"]
        approved = self.metrics["drafts_approved"]
        approval_rate = (approved / total_drafts) if total_drafts > 0 else 1.0

        total_sends = self.metrics["sends_attempted"]
        successful = self.metrics["sends_successful"]
        success_rate = (successful / total_sends) if total_sends > 0 else 1.0

        return {
            **self.metrics,
            "draft_approval_rate": round(approval_rate, 3),
            "send_success_rate": round(success_rate, 3),
        }
