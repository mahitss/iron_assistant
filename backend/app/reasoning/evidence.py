"""Evidence Evaluation, Conflict Detection, and Source Independence Engine (Task 71).

Enforces:
1. Evidence evaluation (relevance, reliability, freshness, trust levels).
2. Source Independence: Copying/repeating claims across agents does NOT count as independent evidence.
3. Conflict Detection: Conflicting observations are surfaced, never silently merged.
4. Prompt-Injection Defense: External retrieved content is treated strictly as data, never as system instructions.
"""

from datetime import UTC, datetime

from app.reasoning.schemas import ReasoningEvidence


def utc_now() -> datetime:
    return datetime.now(UTC)


class EvidenceEvaluator:
    """Evaluates evidence validity, clusters independent sources, and flags contradictions."""

    INJECTION_INDICATORS = [
        "ignore all previous instructions",
        "ignore previous instructions",
        "system prompt override",
        "you are now in developer mode",
        "disregard safety guidelines",
        "expose credentials",
        "print your prompt",
    ]

    @classmethod
    def sanitize_content(cls, content: str) -> tuple[str, bool]:
        """Strip prompt injection attempts and treat content strictly as inert observation data."""
        c_lower = content.lower()
        is_injection_attempt = any(ind in c_lower for ind in cls.INJECTION_INDICATORS)
        if is_injection_attempt:
            # Neutralize instruction payload by framing strictly as verbatim data
            sanitized = (
                f"[EXTERNAL_UNTRUSTED_CONTENT] [DATA ONLY - INSTRUCTION OVERRIDE NEUTRALIZED]: {content}"
            )
            return sanitized, True
        return content, False

    @classmethod
    def create_evidence(
        cls,
        source_type: str = "observation",
        source_id: str = "src-01",
        content_summary: str = "",
        raw_data: dict | None = None,
        trust_level: str = "KNOWN_SOURCE",
        reliability: float = 0.8,
        relevance: float = 0.8,
        independence_group: str = "default",
    ) -> ReasoningEvidence:
        """Helper to create and evaluate an empirical evidence item."""
        ev = ReasoningEvidence(
            source_type=source_type,
            source_id=source_id,
            content_summary=content_summary,
            raw_data=raw_data or {},
            trust_level=trust_level,
            reliability=reliability,
            relevance=relevance,
            independence_group=independence_group,
        )
        return cls.evaluate_item(ev)

    @classmethod
    def evaluate_reliability_and_freshness(
        cls,
        item: ReasoningEvidence,
        as_of: datetime | None = None,
    ) -> ReasoningEvidence:
        """Alias for evaluate_item."""
        return cls.evaluate_item(item, as_of)

    @classmethod
    def evaluate_item(
        cls,
        item: ReasoningEvidence,
        as_of: datetime | None = None,
    ) -> ReasoningEvidence:
        """Score reliability and freshness."""
        now = as_of or utc_now()
        age_sec = (now - item.timestamp).total_seconds()

        # Sanitize content
        clean_text, was_injection = cls.sanitize_content(item.content_summary)
        item.content_summary = clean_text

        # Penalize reliability if suspicious or prompt injection detected
        if was_injection or item.trust_level in ("SUSPICIOUS", "QUARANTINED"):
            item.reliability = min(item.reliability, 0.2)
            item.trust_level = "QUARANTINED"
        elif item.trust_level == "VERIFIED":
            item.reliability = max(item.reliability, 0.95)
        elif item.trust_level == "TRUSTED":
            item.reliability = max(item.reliability, 0.85)
        elif item.trust_level == "UNVERIFIED":
            item.reliability = min(item.reliability, 0.5)

        # Freshness penalty: older than 1 hour -> slight penalty; older than 24 hours -> decay
        if age_sec > 86400:
            item.reliability = round(item.reliability * 0.7, 3)
        elif age_sec > 3600:
            item.reliability = round(item.reliability * 0.9, 3)

        return item

    @classmethod
    def evaluate_source_independence(
        cls,
        evidence_items: list[ReasoningEvidence],
    ) -> dict[str, list[str]]:
        """Group evidence by independence group to prevent false consensus from mirrored agent claims."""
        groups: dict[str, list[str]] = {}
        for ev in evidence_items:
            grp = ev.independence_group or ev.source_id
            groups.setdefault(grp, []).append(ev.evidence_id)
        return groups

    @classmethod
    def detect_conflicts(
        cls,
        evidence_items: list[ReasoningEvidence],
    ) -> list[tuple[ReasoningEvidence, ReasoningEvidence, str]]:
        """Detect and link contradictory evidence without silently discarding conflicts."""
        conflicts: list[tuple[ReasoningEvidence, ReasoningEvidence, str]] = []

        for i, e1 in enumerate(evidence_items):
            for e2 in evidence_items[i + 1 :]:
                # Check for metric disagreements in raw data
                m1 = e1.raw_data.get("metric_name")
                m2 = e2.raw_data.get("metric_name")
                if m1 and m2 and m1 == m2:
                    v1 = e1.raw_data.get("value")
                    v2 = e2.raw_data.get("value")
                    if (
                        v1 is not None
                        and v2 is not None
                        and isinstance(v1, (int, float))
                        and isinstance(v2, (int, float))
                    ):
                        # If values differ by more than 30% for the same metric
                        if abs(v1 - v2) > (max(abs(v1), abs(v2)) * 0.3):
                            reason = f"Metric conflict on '{m1}': {v1} vs {v2}"
                            e1.is_conflict = True
                            e2.is_conflict = True
                            if e2.evidence_id not in e1.conflicting_evidence_ids:
                                e1.conflicting_evidence_ids.append(e2.evidence_id)
                            if e1.evidence_id not in e2.conflicting_evidence_ids:
                                e2.conflicting_evidence_ids.append(e1.evidence_id)
                            conflicts.append((e1, e2, reason))

                # Check general numeric metric keys in raw data
                common_keys = set(e1.raw_data.keys()) & set(e2.raw_data.keys())
                for k in common_keys:
                    if k in ("host", "environment", "timestamp", "source", "scope", "metric_name", "value"):
                        continue
                    v1 = e1.raw_data.get(k)
                    v2 = e2.raw_data.get(k)
                    if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                        if abs(v1 - v2) > (max(abs(v1), abs(v2)) * 0.3):
                            reason = f"Metric conflict on '{k}': {v1} vs {v2}"
                            e1.is_conflict = True
                            e2.is_conflict = True
                            if e2.evidence_id not in e1.conflicting_evidence_ids:
                                e1.conflicting_evidence_ids.append(e2.evidence_id)
                            if e1.evidence_id not in e2.conflicting_evidence_ids:
                                e2.conflicting_evidence_ids.append(e1.evidence_id)
                            conflicts.append((e1, e2, reason))

                # Check for direct text negation
                t1 = e1.content_summary.lower()
                t2 = e2.content_summary.lower()
                if ("normal" in t1 and "unstable" in t2) or ("healthy" in t1 and "failed" in t2):
                    reason = f"Direct status disagreement: '{e1.content_summary[:30]}' vs '{e2.content_summary[:30]}'"
                    e1.is_conflict = True
                    e2.is_conflict = True
                    if e2.evidence_id not in e1.conflicting_evidence_ids:
                        e1.conflicting_evidence_ids.append(e2.evidence_id)
                    if e1.evidence_id not in e2.conflicting_evidence_ids:
                        e2.conflicting_evidence_ids.append(e1.evidence_id)
                    conflicts.append((e1, e2, reason))

        return conflicts
