"""Sequence Preservation, Out-of-Order Event Handling, and Reordering Buffers (Task 46)."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.perception.events import PerceptionEvent

logger = logging.getLogger("kairo.perception.ordering")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventOrderManager:
    """Tracks sequence numbers per source/subject and manages out-of-order buffers (Spec 18, 19)."""

    def __init__(self, buffer_window_seconds: float = 5.0) -> None:
        self.buffer_window_seconds = buffer_window_seconds
        # stream_key -> highest observed sequence number
        self._highest_sequences: Dict[str, int] = {}
        # stream_key -> list of out-of-order buffered events
        self._buffers: Dict[str, List[PerceptionEvent]] = {}

    def _get_stream_key(self, event: PerceptionEvent) -> str:
        return f"{event.source_id}:{event.subject}"

    def check_sequence(self, event: PerceptionEvent) -> tuple[bool, str]:
        """Verify if event arrives in proper sequential order (Spec 18, 19).
        
        Returns:
            (is_in_order, status_reason): IN_ORDER, OUT_OF_ORDER, or UNSEQUENCED
        """
        if event.sequence <= 0:
            return True, "UNSEQUENCED"

        key = self._get_stream_key(event)
        last_seq = self._highest_sequences.get(key, 0)

        if event.sequence == last_seq + 1:
            self._highest_sequences[key] = event.sequence
            return True, "IN_ORDER"
        elif event.sequence > last_seq + 1:
            logger.warning(
                "Gap in event stream %s: expected %d, got %d. Buffering for late arrival.",
                key,
                last_seq + 1,
                event.sequence,
            )
            self._buffers.setdefault(key, []).append(event)
            self._highest_sequences[key] = max(last_seq, event.sequence)
            return True, "GAP_DETECTED"
        else:
            # event.sequence <= last_seq: Late out-of-order event
            logger.info("Late out-of-order event for %s (seq %d <= last %d)", key, event.sequence, last_seq)
            return False, "OUT_OF_ORDER"

    def get_last_sequence(self, source_id: str, subject: str) -> int:
        return self._highest_sequences.get(f"{source_id}:{subject}", 0)
