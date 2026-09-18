"""Candidate Gathering Engine for Task 110:
Collects candidate context elements from across existing Kairo subsystems.
Preserves source identity, trust labels, and epistemic boundaries.

Strict Invariants:
- External content remains untrusted data (never gains system authority).
- Never flattens all candidates into anonymous unlabelled text.
- Consumes upstream subsystems (Attention, Intent, Belief, Memory, World State, Self-Model, Missions, Decisions).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Optional

from app.context.working_set_domain import (
    ContextAssemblyRequest,
    ContextCandidate,
    ContextSectionType,
    TrustClassification,
    gen_ctx_id,
    utc_now,
)


class CandidateGatheringEngine:
    """Gathers candidate context items across Kairo subsystems without collapsing provenance."""

    @classmethod
    def gather_candidates(
        cls,
        request: ContextAssemblyRequest,
        mock_inputs: Optional[Dict[str, Any]] = None,
    ) -> List[ContextCandidate]:
        """Gather candidates across available subsystems, incorporating real services or explicit inputs."""
        candidates: List[ContextCandidate] = []
        inputs = mock_inputs or {}

        # 1. User Request & Active Intent (Task 108)
        user_text = request.explicit_user_request or request.objective
        if user_text:
            candidates.append(
                ContextCandidate(
                    candidate_id=gen_ctx_id("cand_req"),
                    source_subsystem="intent",
                    source_id=request.current_intent_id or "intent_direct",
                    source_timestamp=utc_now(),
                    title="Current User Request",
                    raw_content=user_text,
                    structured_data={
                        "user_scope": request.user_scope,
                        "operation_type": request.operation_type,
                        "objective": request.objective,
                    },
                    trust_label=TrustClassification.USER_AUTHORED,
                    preliminary_relevance=1.0,
                    domain_volatility=0.2,
                    is_untrusted=False,
                )
            )

        # 2. Active Focus & Attention Signals (Task 109)
        # Attempt to inspect live AttentionEngineService if present
        focus_data = inputs.get("attention_focus")
        if not focus_data:
            try:
                from app.attention.service import AttentionEngineService
                attn_svc = AttentionEngineService.get_instance()
                active_focus = attn_svc.focus_mgr.get_active_session()
                if active_focus:
                    focus_data = {
                        "session_id": active_focus.session_id,
                        "target_title": active_focus.target.title,
                        "target_type": active_focus.target.target_type,
                        "stack_depth": attn_svc.focus_mgr.get_stack_depth(),
                    }
            except Exception:
                pass

        if focus_data:
            candidates.append(
                ContextCandidate(
                    candidate_id=gen_ctx_id("cand_attn"),
                    source_subsystem="attention",
                    source_id=focus_data.get("session_id", "attn_active"),
                    source_timestamp=utc_now(),
                    title=f"Active Attention Focus: {focus_data.get('target_title', 'Core Deliberation')}",
                    raw_content=f"Attention target: {focus_data.get('target_title')}, Depth: {focus_data.get('stack_depth', 0)}",
                    structured_data=focus_data,
                    trust_label=TrustClassification.SYSTEM_DERIVED,
                    preliminary_relevance=0.95,
                    domain_volatility=0.8,
                )
            )

        # 3. Active Mission & Goal State (Task 100)
        mission_data = inputs.get("mission")
        if mission_data:
            candidates.append(
                ContextCandidate(
                    candidate_id=gen_ctx_id("cand_msn"),
                    source_subsystem="missions",
                    source_id=mission_data.get("mission_id", "msn_active"),
                    source_timestamp=utc_now(),
                    title=f"Active Mission: {mission_data.get('title', 'System Objective')}",
                    raw_content=mission_data.get("description", "Active mission objective"),
                    structured_data=mission_data,
                    trust_label=TrustClassification.SYSTEM_DERIVED,
                    preliminary_relevance=0.90,
                    domain_volatility=0.4,
                )
            )

        # 4. Reconciled World State (Task 98)
        world_data = inputs.get("world_state")
        if world_data:
            for obs in world_data if isinstance(world_data, list) else [world_data]:
                is_untrusted_source = obs.get("is_untrusted", False)
                candidates.append(
                    ContextCandidate(
                        candidate_id=gen_ctx_id("cand_wrld"),
                        source_subsystem="world_state",
                        source_id=obs.get("entity_id", "entity_world"),
                        source_timestamp=obs.get("timestamp", utc_now()),
                        title=f"Observed World State: {obs.get('key', 'environment')}",
                        raw_content=str(obs.get("value", "")),
                        structured_data=obs,
                        trust_label=TrustClassification.EXTERNAL_UNTRUSTED if is_untrusted_source else TrustClassification.OBSERVED,
                        preliminary_relevance=0.85,
                        domain_volatility=obs.get("volatility", 0.5),
                        is_untrusted=is_untrusted_source,
                    )
                )

        # 5. Beliefs & Arbitrated Claims (Task 107)
        belief_data = inputs.get("beliefs")
        if belief_data:
            for b in belief_data if isinstance(belief_data, list) else [belief_data]:
                candidates.append(
                    ContextCandidate(
                        candidate_id=gen_ctx_id("cand_blf"),
                        source_subsystem="belief",
                        source_id=b.get("belief_id", "blf_claim"),
                        source_timestamp=b.get("timestamp", utc_now()),
                        title=f"Belief Claim: {b.get('subject', 'domain')}",
                        raw_content=b.get("claim", ""),
                        structured_data=b,
                        trust_label=TrustClassification.MODEL_DERIVED,
                        preliminary_relevance=0.80,
                        domain_volatility=0.3,
                    )
                )

        # 6. Cognitive Memory & Experience Consolidation (Task 103)
        memory_data = inputs.get("cognitive_memory")
        if memory_data:
            for m in memory_data if isinstance(memory_data, list) else [memory_data]:
                candidates.append(
                    ContextCandidate(
                        candidate_id=gen_ctx_id("cand_mem"),
                        source_subsystem="cognitive_memory",
                        source_id=m.get("memory_id", "mem_exp"),
                        source_timestamp=m.get("timestamp", utc_now()),
                        title=f"Relevant Memory: {m.get('topic', 'historical_lesson')}",
                        raw_content=m.get("summary", ""),
                        structured_data=m,
                        trust_label=TrustClassification.SYSTEM_DERIVED,
                        preliminary_relevance=0.75,
                        domain_volatility=0.1,
                    )
                )

        # 7. Self-Model & Internal Runtime State (Task 101)
        self_model_data = inputs.get("self_model")
        if self_model_data:
            candidates.append(
                ContextCandidate(
                    candidate_id=gen_ctx_id("cand_slf"),
                    source_subsystem="self_model",
                    source_id="self_model_runtime",
                    source_timestamp=utc_now(),
                    title="Self-Model & Capability Status",
                    raw_content=f"Health: {self_model_data.get('health_status', 'HEALTHY')}, Known limitations: {self_model_data.get('limitations', 'none')}",
                    structured_data=self_model_data,
                    trust_label=TrustClassification.SYSTEM_DERIVED,
                    preliminary_relevance=0.70,
                    domain_volatility=0.4,
                )
            )

        # 8. Decision Intelligence Deliberation Records (Task 94)
        decision_data = inputs.get("decision")
        if decision_data:
            candidates.append(
                ContextCandidate(
                    candidate_id=gen_ctx_id("cand_dec"),
                    source_subsystem="decision",
                    source_id=decision_data.get("decision_id", "dec_rec"),
                    source_timestamp=utc_now(),
                    title=f"Prior Decision: {decision_data.get('objective', 'Strategic Option')}",
                    raw_content=decision_data.get("selected_option", ""),
                    structured_data=decision_data,
                    trust_label=TrustClassification.SYSTEM_DERIVED,
                    preliminary_relevance=0.75,
                    domain_volatility=0.3,
                )
            )

        # 9. Untrusted External Ingestions (Web, Tool, Git)
        external_data = inputs.get("external_untrusted")
        if external_data:
            for ext in external_data if isinstance(external_data, list) else [external_data]:
                candidates.append(
                    ContextCandidate(
                        candidate_id=gen_ctx_id("cand_untrusted"),
                        source_subsystem=ext.get("subsystem", "web_fetch"),
                        source_id=ext.get("source_id", "ext_payload"),
                        source_timestamp=utc_now(),
                        title=f"External Web/Tool Content: {ext.get('url', 'untrusted_source')}",
                        raw_content=ext.get("body", ""),
                        structured_data=ext,
                        trust_label=TrustClassification.EXTERNAL_UNTRUSTED,
                        preliminary_relevance=0.60,
                        domain_volatility=0.9,
                        is_untrusted=True,
                    )
                )

        return candidates
