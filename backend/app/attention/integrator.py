"""Subsystem Integrator for Kairo Attention & Cognitive Resource Engine (Task 70).

Bridges Attention Engine with:
- Incidents (Task 61)
- Situational Awareness (Task 60)
- Autonomous Goals & Missions (Task 66)
- Metacognitive Self-Audit (Task 67)
- Memory Consolidation (Task 68)
- Universal Context & Personalization (Task 69)
- Executive Decision Engine (Task 57)
- Human User Notification Prioritization
"""

from typing import Any

from app.attention.schemas import AttentionCandidate, NotificationPriority


class SubsystemIntegrator:
    """Coordinates signals, snapshots, audits, and notifications across subsystems."""

    @classmethod
    def aggregate_event_flood(
        cls,
        *,
        events: list[dict[str, Any]],
        threshold_count: int = 5,
    ) -> list[dict[str, Any]]:
        """Prevent low-level event floods from overwhelming attention (Task 60).

        Aggregates multiple similar events (e.g. 100 failed requests) into a single
        correlated pattern candidate while preserving provenance.
        """
        if len(events) < threshold_count:
            return events

        # Group by event_type
        grouped: dict[str, list[dict[str, Any]]] = {}
        for ev in events:
            etype = ev.get("event_type", "general")
            grouped.setdefault(etype, []).append(ev)

        aggregated: list[dict[str, Any]] = []
        for etype, group in grouped.items():
            if len(group) >= threshold_count:
                # Aggregate into pattern
                summary_cand = {
                    "source_type": "event_correlation",
                    "source_id": f"corr-{etype}-{len(group)}",
                    "event_type": etype,
                    "title": f"Elevated pattern: {len(group)} '{etype}' events detected",
                    "description": f"Aggregated {len(group)} raw occurrences to prevent cognitive attention flood.",
                    "importance": min(0.9, 0.4 + (len(group) * 0.05)),
                    "urgency": min(0.9, 0.5 + (len(group) * 0.04)),
                    "severity": "HIGH" if len(group) > 20 else "MEDIUM",
                    "risk": min(0.85, 0.3 + (len(group) * 0.05)),
                    "relevance": 0.8,
                    "novelty": 0.6,
                    "provenance": {
                        "raw_event_count": len(group),
                        "first_seen": group[0].get("timestamp"),
                        "last_seen": group[-1].get("timestamp"),
                        "raw_sample_ids": [g.get("id") for g in group[:5]],
                    },
                }
                aggregated.append(summary_cand)
            else:
                aggregated.extend(group)

        return aggregated

    @classmethod
    def determine_notification_tier(
        cls,
        candidate: AttentionCandidate,
        user_preferences: dict[str, Any] | None = None,
    ) -> tuple[NotificationPriority, str]:
        """Determine appropriate notification priority for human attention.

        Human attention is a finite resource; avoids notification spam.
        Critical safety items are NEVER suppressed.
        """
        prefs = user_preferences or {}
        quiet_hours = prefs.get("quiet_hours", False)
        min_notif_threshold = prefs.get("min_notification_score", 0.65)

        # 1. Critical safety invariant: critical urgency or severity always urgent
        if candidate.severity == "CRITICAL" or candidate.urgency >= 0.85:
            return (
                NotificationPriority.URGENT_NOTIFY,
                "Critical safety/incident: bypasses user quiet hours and filters.",
            )

        # 2. Quiet hours check for non-critical
        if quiet_hours:
            if candidate.urgency >= 0.70:
                return NotificationPriority.DIGEST, "Deferred to digest due to quiet hours preference."
            return NotificationPriority.SILENT, "Silenced by user quiet hours."

        # 3. Standard score mapping
        if candidate.attention_score >= 0.75:
            return NotificationPriority.NOTIFY, "High attention score warrants prompt user notification."
        if candidate.attention_score >= min_notif_threshold:
            return NotificationPriority.DIGEST, "Moderate attention score queued for summary digest."
        if candidate.attention_score >= 0.30:
            return NotificationPriority.LOG, "Recorded in system log without interruption."

        return NotificationPriority.SILENT, "Low attention score; completely silent."

    @classmethod
    def run_metacognitive_audit(
        cls,
        current_focus: AttentionCandidate | None,
        queue: list[AttentionCandidate],
        deferred: list[AttentionCandidate],
        monitoring: list[AttentionCandidate],
    ) -> list[str]:
        """Perform autonomous metacognitive attention audit (Task 67).

        Asks:
        - Am I focusing on the right thing?
        - Am I ignoring something important in the queue?
        - Have I deferred something repeatedly?
        - Is an untrusted source driving high attention?
        """
        critiques: list[str] = []

        # 1. Check if current focus is low priority while high priority items wait
        if current_focus:
            for q in queue:
                if q.attention_score > (current_focus.attention_score + 0.3) and q.urgency > 0.7:
                    critiques.append(
                        f"Metacognitive critique: Focusing on '{current_focus.title}' (score={current_focus.attention_score:.2f}) "
                        f"while higher priority item '{q.title}' (score={q.attention_score:.2f}) is queued."
                    )

        # 2. Check for repeated deferral / goal starvation
        for d in deferred:
            if d.deferral_count >= 3:
                critiques.append(
                    f"Starvation warning: Item '{d.title}' has been deferred {d.deferral_count} times; "
                    "scheduling fairness aging required."
                )

        # 3. Check for untrusted sources with inflated urgency claims
        for item in [current_focus] + queue if current_focus else queue:
            prov = item.provenance or {}
            if not prov.get("is_trusted", True) and item.urgency >= 0.8:
                critiques.append(
                    f"Epistemic warning: Candidate '{item.title}' claims critical urgency ({item.urgency:.2f}) "
                    "from an untrusted or unverified source."
                )

        if not critiques:
            critiques.append(
                "Metacognitive attention audit clean: focus and scheduling align with priorities."
            )

        return critiques
