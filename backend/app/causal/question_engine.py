"""Causal Question Engine supporting natural and structured causal queries (Task 73, Spec 34).

Answers:
1. What caused X?
2. What affects Y?
3. What would happen if X changed (What-if / DO(X))?
4. What factors mediate Y?
5. What factors confound X and Y?
6. What should we intervene on?
7. Which cause has strongest evidence?
8. What evidence would disprove this relationship?
"""

from __future__ import annotations

import logging
from typing import Any

from app.causal.discovery_schemas import (
    CausalQuestionRequest,
    CausalQuestionResponse,
    CausalQuestionType,
    CausalRelationship,
    CausalRelationshipState,
)

logger = logging.getLogger(__name__)


class CausalQuestionEngine:
    """Answers queries regarding cause, effect, intervention, mediation, and falsification."""

    @staticmethod
    def answer_query(
        request: CausalQuestionRequest,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        """Route and answer one of the 8 core causal questions."""
        q_type = request.question_type
        target_entity = request.entity
        target_var = request.variable

        if q_type == CausalQuestionType.WHAT_CAUSED_X:
            return CausalQuestionEngine._answer_what_caused_x(target_entity, target_var, relationships)

        if q_type == CausalQuestionType.WHAT_AFFECTS_Y:
            return CausalQuestionEngine._answer_what_affects_y(target_entity, target_var, relationships)

        if q_type == CausalQuestionType.WHAT_WOULD_HAPPEN_IF_X:
            return CausalQuestionEngine._answer_what_if_x(
                target_entity, target_var, request.target_value, relationships
            )

        if q_type == CausalQuestionType.WHAT_FACTORS_MEDIATE_Y:
            return CausalQuestionEngine._answer_mediators(
                request.comparison_entity or target_entity,
                request.comparison_variable or target_var or "",
                target_entity,
                target_var or "",
                relationships,
            )

        if q_type == CausalQuestionType.WHAT_FACTORS_CONFOUND:
            return CausalQuestionEngine._answer_confounders(
                target_entity,
                target_var or "",
                request.comparison_entity or "",
                request.comparison_variable or "",
                relationships,
            )

        if q_type == CausalQuestionType.WHAT_SHOULD_WE_INTERVENE_ON:
            return CausalQuestionEngine._answer_what_to_intervene(target_entity, target_var, relationships)

        if q_type == CausalQuestionType.WHICH_CAUSE_STRONGEST:
            return CausalQuestionEngine._answer_strongest_cause(target_entity, target_var, relationships)

        if q_type == CausalQuestionType.WHAT_WOULD_DISPROVE:
            return CausalQuestionEngine._answer_what_would_disprove(
                target_entity, target_var, request.comparison_entity, request.comparison_variable, relationships
            )

        return CausalQuestionResponse(
            question_type=q_type,
            query=f"Unknown question for {target_entity}",
            answer="Question type not recognized.",
            confidence=0.0,
        )

    @staticmethod
    def _answer_what_caused_x(
        entity: str,
        variable: str | None,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        matches = [
            r for r in relationships
            if r.effect_entity == entity and (variable is None or r.effect_variable == variable)
        ]
        # Sort by status priority (VERIFIED > STRONGLY_SUPPORTED > SUPPORTED > HYPOTHESIZED) and confidence
        state_ranks = {
            CausalRelationshipState.VERIFIED: 4,
            CausalRelationshipState.STRONGLY_SUPPORTED: 3,
            CausalRelationshipState.SUPPORTED: 2,
            CausalRelationshipState.HYPOTHESIZED: 1,
        }
        matches.sort(key=lambda r: (state_ranks.get(r.status, 0), r.confidence), reverse=True)

        if not matches:
            return CausalQuestionResponse(
                question_type=CausalQuestionType.WHAT_CAUSED_X,
                query=f"What caused {entity}:{variable or '*'}",
                answer=f"No verified or supported causes identified for {entity}:{variable or '*'}.",
                confidence=0.1,
                uncertainty="Lack of empirical observation or experiment linking to this node.",
            )

        primary = matches[0]
        candidate_causes = [
            {
                "cause": f"{m.cause_entity}:{m.cause_variable}",
                "status": m.status.value,
                "confidence": m.confidence,
                "mechanism": m.mechanism,
                "strength": m.strength.value,
            }
            for m in matches
        ]

        ans = (
            f"Leading cause for {entity}:{primary.effect_variable} is "
            f"{primary.cause_entity}:{primary.cause_variable} (status: {primary.status.value}, "
            f"confidence: {primary.confidence:.2f}, mechanism: {primary.mechanism})."
        )

        return CausalQuestionResponse(
            question_type=CausalQuestionType.WHAT_CAUSED_X,
            query=f"What caused {entity}:{variable or '*'}",
            answer=ans,
            candidate_causes=candidate_causes,
            supporting_evidence=primary.evidence_refs,
            confidence=primary.confidence,
            falsification_criteria=primary.falsification_criteria,
            scope=primary.scope,
            environment=primary.environment,
        )

    @staticmethod
    def _answer_what_affects_y(
        entity: str,
        variable: str | None,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        return CausalQuestionEngine._answer_what_caused_x(entity, variable, relationships)

    @staticmethod
    def _answer_what_if_x(
        entity: str,
        variable: str | None,
        target_value: Any | None,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        downstream = [
            r for r in relationships
            if r.cause_entity == entity and (variable is None or r.cause_variable == variable)
        ]
        if not downstream:
            return CausalQuestionResponse(
                question_type=CausalQuestionType.WHAT_WOULD_HAPPEN_IF_X,
                query=f"What would happen if {entity}:{variable or '*'} changed to {target_value}?",
                answer=f"No verified downstream causal impacts mapped from {entity}:{variable or '*'}.",
                confidence=0.3,
            )

        effects_summary: list[dict[str, Any]] = []
        for d in downstream:
            delta = 1.0 if d.direction.value == "POSITIVE" else (-1.0 if d.direction.value == "NEGATIVE" else 0.0)
            effects_summary.append({
                "affected_entity": d.effect_entity,
                "affected_variable": d.effect_variable,
                "direction": d.direction.value,
                "expected_delta": delta,
                "confidence": d.confidence,
                "status": d.status.value,
            })

        ans = (
            f"Intervening on {entity}:{variable or '*'} is predicted to affect {len(downstream)} downstream variable(s): "
            + ", ".join([f"{e['affected_entity']}:{e['affected_variable']} ({e['direction']})" for e in effects_summary])
        )

        return CausalQuestionResponse(
            question_type=CausalQuestionType.WHAT_WOULD_HAPPEN_IF_X,
            query=f"What would happen if {entity}:{variable or '*'} changed to {target_value}?",
            answer=ans,
            candidate_causes=effects_summary,
            confidence=round(sum(e["confidence"] for e in effects_summary) / len(effects_summary), 2),
            uncertainty="Non-linear or threshold effects may modulate actual impact depending on system baseline.",
        )

    @staticmethod
    def _answer_mediators(
        cause_entity: str,
        cause_var: str,
        effect_entity: str,
        effect_var: str,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        from app.causal.confounder_engine import ConfounderEngine

        edges_raw = [r.model_dump() for r in relationships]
        med_res = ConfounderEngine.analyze_mediators(cause_entity, cause_var, effect_entity, effect_var, edges_raw)

        return CausalQuestionResponse(
            question_type=CausalQuestionType.WHAT_FACTORS_MEDIATE_Y,
            query=f"What factors mediate {cause_entity}:{cause_var} -> {effect_entity}:{effect_var}?",
            answer=med_res.mechanism_narrative,
            candidate_causes=[{"mediator": m} for m in med_res.mediator_variables],
            confidence=0.8 if med_res.is_mediated else 0.5,
        )

    @staticmethod
    def _answer_confounders(
        entity_a: str,
        var_a: str,
        entity_b: str,
        var_b: str,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        from app.causal.confounder_engine import ConfounderEngine

        edges_raw = [r.model_dump() for r in relationships]
        conf_res = ConfounderEngine.analyze_confounders(entity_a, var_a, entity_b, var_b, edges_raw)

        return CausalQuestionResponse(
            question_type=CausalQuestionType.WHAT_FACTORS_CONFOUND,
            query=f"What factors confound {entity_a}:{var_a} and {entity_b}:{var_b}?",
            answer=conf_res.recommendation or "No confounding common causes detected between specified variables.",
            candidate_causes=[c.model_dump() for c in conf_res.candidate_confounders],
            confidence=conf_res.adjusted_confidence,
        )

    @staticmethod
    def _answer_what_to_intervene(
        target_entity: str,
        target_var: str | None,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        # Find causes that have STRONG strength and VERIFIED/SUPPORTED status
        candidates = [
            r for r in relationships
            if r.effect_entity == target_entity and (target_var is None or r.effect_variable == target_var)
            and r.status in {CausalRelationshipState.VERIFIED, CausalRelationshipState.STRONGLY_SUPPORTED, CausalRelationshipState.SUPPORTED}
        ]
        candidates.sort(key=lambda r: (r.strength.value == "STRONG", r.confidence), reverse=True)

        if not candidates:
            return CausalQuestionResponse(
                question_type=CausalQuestionType.WHAT_SHOULD_WE_INTERVENE_ON,
                query=f"What should we intervene on to change {target_entity}:{target_var or '*'}",
                answer="No established actionable root causes found to intervene on.",
                confidence=0.2,
            )

        rec = candidates[0]
        ans = (
            f"Recommended intervention target: DO({rec.cause_entity}:{rec.cause_variable}). "
            f"Expected to directly modulate {rec.effect_entity}:{rec.effect_variable} "
            f"with {rec.strength.value} strength and confidence {rec.confidence:.2f}."
        )

        return CausalQuestionResponse(
            question_type=CausalQuestionType.WHAT_SHOULD_WE_INTERVENE_ON,
            query=f"What should we intervene on to change {target_entity}:{target_var or '*'}",
            answer=ans,
            candidate_causes=[{"target": f"{rec.cause_entity}:{rec.cause_variable}", "status": rec.status.value}],
            confidence=rec.confidence,
        )

    @staticmethod
    def _answer_strongest_cause(
        entity: str,
        variable: str | None,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        return CausalQuestionEngine._answer_what_caused_x(entity, variable, relationships)

    @staticmethod
    def _answer_what_would_disprove(
        entity_a: str,
        var_a: str | None,
        entity_b: str | None,
        var_b: str | None,
        relationships: list[CausalRelationship],
    ) -> CausalQuestionResponse:
        matches = [
            r for r in relationships
            if r.cause_entity == entity_a
            and (entity_b is None or r.effect_entity == entity_b)
            and (var_b is None or r.effect_variable == var_b)
        ]
        if not matches:
            return CausalQuestionResponse(
                question_type=CausalQuestionType.WHAT_WOULD_DISPROVE,
                query=f"What evidence would disprove {entity_a} -> {entity_b or '*'}",
                answer="No matching causal relationship found to evaluate falsification.",
                confidence=0.0,
            )

        rel = matches[0]
        criteria = rel.falsification_criteria or [
            f"Controlled intervention on {rel.cause_entity}:{rel.cause_variable} yields no change in {rel.effect_entity}:{rel.effect_variable}",
            f"Preceding temporal event logs prove {rel.effect_entity} change began before {rel.cause_entity} intervention",
        ]

        ans = (
            f"Falsification criteria for {rel.cause_entity}:{rel.cause_variable} -> "
            f"{rel.effect_entity}:{rel.effect_variable}: " + "; ".join(criteria)
        )

        return CausalQuestionResponse(
            question_type=CausalQuestionType.WHAT_WOULD_DISPROVE,
            query=f"What evidence would disprove {rel.cause_entity} -> {rel.effect_entity}",
            answer=ans,
            falsification_criteria=criteria,
            confidence=rel.confidence,
        )
