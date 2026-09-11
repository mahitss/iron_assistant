"""ContextConflictDetector: Detects contradictory context items without silent overwrites (Task 69)."""

import logging
import re

from app.context.universal_schemas import ContextConflictItem, UniversalContextItem

logger = logging.getLogger("kairo.context.conflicts")


class ContextConflictDetector:
    """Detects contradictions, temporal discrepancies, and conflicting claims across context items."""

    POLARITY_PAIRS = [
        ("healthy", "unhealthy"),
        ("active", "inactive"),
        ("online", "offline"),
        ("enabled", "disabled"),
        ("success", "failure"),
        ("passed", "failed"),
        ("up", "down"),
    ]

    PROPERTY_PATTERNS = [
        re.compile(
            r"\b(port|timeout|version|database|retries|environment)\s*[:=]\s*([a-zA-Z0-9_\.-]+)",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def detect_conflicts(
        cls,
        items: list[UniversalContextItem],
    ) -> list[ContextConflictItem]:
        """Analyze pairs of context items for direct or property-level contradictions."""
        conflicts: list[ContextConflictItem] = []
        n = len(items)

        for i in range(n):
            for j in range(i + 1, n):
                item_a = items[i]
                item_b = items[j]

                # 1. Check direct polarity opposites on similar titles/subjects
                has_polarity_conflict, reason = cls._check_polarity_conflict(item_a, item_b)
                if has_polarity_conflict:
                    temporal_diff = cls._format_temporal_difference(item_a, item_b)
                    status = (
                        "TEMPORAL_SUPERSEDED" if temporal_diff and "newer" in temporal_diff else "UNRESOLVED"
                    )
                    conflicts.append(
                        ContextConflictItem(
                            subject=f"{item_a.title} vs {item_b.title}",
                            item_a_id=item_a.item_id,
                            item_b_id=item_b.item_id,
                            claim_a=item_a.content[:120],
                            claim_b=item_b.content[:120],
                            source_a=item_a.source_type,
                            source_b=item_b.source_type,
                            timestamp_a=item_a.timestamp,
                            timestamp_b=item_b.timestamp,
                            environment_a=item_a.environment,
                            environment_b=item_b.environment,
                            reason=reason,
                            temporal_difference=temporal_diff,
                            resolution_status=status,
                        )
                    )
                    continue

                # 2. Check property value mismatch
                has_prop_conflict, prop_reason = cls._check_property_conflict(item_a, item_b)
                if has_prop_conflict:
                    temporal_diff = cls._format_temporal_difference(item_a, item_b)
                    status = (
                        "TEMPORAL_SUPERSEDED" if temporal_diff and "newer" in temporal_diff else "UNRESOLVED"
                    )
                    conflicts.append(
                        ContextConflictItem(
                            subject=f"Property mismatch in {item_a.title}",
                            item_a_id=item_a.item_id,
                            item_b_id=item_b.item_id,
                            claim_a=item_a.content[:120],
                            claim_b=item_b.content[:120],
                            source_a=item_a.source_type,
                            source_b=item_b.source_type,
                            timestamp_a=item_a.timestamp,
                            timestamp_b=item_b.timestamp,
                            environment_a=item_a.environment,
                            environment_b=item_b.environment,
                            reason=prop_reason,
                            temporal_difference=temporal_diff,
                            resolution_status=status,
                        )
                    )

        return conflicts

    @classmethod
    def _check_polarity_conflict(
        cls,
        a: UniversalContextItem,
        b: UniversalContextItem,
    ) -> tuple[bool, str]:
        text_a = f"{a.title} {a.content}".lower()
        text_b = f"{b.title} {b.content}".lower()

        for pos, neg in cls.POLARITY_PAIRS:
            if (pos in text_a and neg in text_b) or (neg in text_a and pos in text_b):
                # Ensure they share a common subject keyword
                words_a = set(text_a.split())
                words_b = set(text_b.split())
                shared = words_a.intersection(words_b) - {pos, neg, "the", "a", "is", "of", "and", "in"}
                if len(shared) >= 1:
                    return (
                        True,
                        f"Opposing polarities ('{pos}' vs '{neg}') detected for subject '{list(shared)[0]}'",
                    )
        return False, ""

    @classmethod
    def _check_property_conflict(
        cls,
        a: UniversalContextItem,
        b: UniversalContextItem,
    ) -> tuple[bool, str]:
        matches_a: dict[str, str] = {}
        matches_b: dict[str, str] = {}

        for pat in cls.PROPERTY_PATTERNS:
            for k, v in pat.findall(a.content):
                matches_a[k.lower()] = v.lower()
            for k, v in pat.findall(b.content):
                matches_b[k.lower()] = v.lower()

        for k in matches_a:
            if k in matches_b and matches_a[k] != matches_b[k]:
                return True, f"Conflicting values for property '{k}': '{matches_a[k]}' vs '{matches_b[k]}'"

        return False, ""

    @classmethod
    def _format_temporal_difference(
        cls,
        a: UniversalContextItem,
        b: UniversalContextItem,
    ) -> str | None:
        if not a.timestamp or not b.timestamp:
            return None
        diff_sec = (a.timestamp - b.timestamp).total_seconds()
        if abs(diff_sec) < 60:
            return "Concurrent timestamps"
        if diff_sec > 0:
            return f"{a.item_id} is {int(diff_sec // 60)} minutes newer than {b.item_id}"
        else:
            return f"{b.item_id} is {int(-diff_sec // 60)} minutes newer than {a.item_id}"
