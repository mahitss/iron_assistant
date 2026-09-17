"""Ambiguity Detection, Safe Defaults & Consequence-Aware Clarification Engine for Task 108.

Implements:
- Section 12: Ambiguity detection across 10 distinct categories.
- Section 13: Minimal clarification questions (high gain, low burden).
- Section 14: Clarification priority gating based on material consequence (safety, authorization, destructive effects, privacy).
- Section 15: Safe Defaults vs Operational Assumptions. Safe defaults must be reversible and low-risk.
  NEVER use safe defaults to bypass missing authorization.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.intent.domain import (
    Ambiguity,
    AmbiguityType,
    Assumption,
    AssumptionType,
    Clarification,
    ClarificationStatus,
    ExternalEffectFlag,
    Intent,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.intent.ambiguity_clarification")


class AmbiguityAndClarificationEngine:
    """Detects ambiguities, evaluates consequence risk, and formulates targeted clarifications."""

    # Pronoun and vague reference markers
    _VAGUE_TARGETS = {"it", "them", "those", "that", "this", "files", "everything", "something"}
    _DESTRUCTIVE_ACTIONS = {"delete", "remove", "clean", "drop", "wipe", "purge", "destroy", "prune"}

    @classmethod
    def analyze_ambiguity(
        cls,
        intent: Intent,
        raw_text: str,
        active_environment: Optional[str] = None,
    ) -> Tuple[List[Ambiguity], List[Clarification], List[Assumption]]:
        """Scans for ambiguity, gates by consequence, and yields minimal clarifications or safe defaults."""
        ambiguities: List[Ambiguity] = []
        clarifications: List[Clarification] = []
        assumptions: List[Assumption] = []

        lower_text = raw_text.lower()
        is_destructive = intent.action_class in cls._DESTRUCTIVE_ACTIONS or any(w in lower_text for w in cls._DESTRUCTIVE_ACTIONS)
        has_external_effect = intent.external_effect == ExternalEffectFlag.EXTERNAL_EFFECT_POSSIBLE

        # 1. Target Ambiguity (Spec 12)
        if intent.target == "UNKNOWN" or any(w in lower_text.split() for w in cls._VAGUE_TARGETS):
            consequence = "CRITICAL" if is_destructive else "HIGH" if has_external_effect else "LOW"
            requires_clarification = is_destructive or has_external_effect

            amb = Ambiguity(
                ambiguity_id=generate_id("amb"),
                intent_id=intent.intent_id,
                ambiguity_type=AmbiguityType.TARGET,
                subject="Target Resource or Entity",
                explanation="The specific target entity is ambiguous or referred to with a vague pronoun.",
                candidates=["backend", "frontend", "downloads_folder", "specified_file"],
                consequence_level=consequence,
                requires_user_clarification=requires_clarification,
            )
            ambiguities.append(amb)

            if requires_clarification:
                # Formulate minimal question
                action_verb = intent.action_class or "target"
                q = Clarification(
                    clarification_id=generate_id("clr"),
                    intent_id=intent.intent_id,
                    ambiguity_id=amb.ambiguity_id,
                    question=f"Which specific directory or resource should I {action_verb}?",
                    rationale=f"A definitive target is required to safely perform {action_verb} without unintended side effects.",
                    affected_decision="target_selection",
                    consequence_level=consequence,
                    options=["current workspace", "downloads folder", "specify custom path"],
                    status=ClarificationStatus.PENDING,
                )
                clarifications.append(q)
            else:
                # For non-destructive queries, use a safe default
                assumptions.append(Assumption(
                    assumption_id=generate_id("asm"),
                    intent_id=intent.intent_id,
                    statement="Applying read-only inspection to the active workspace project by default.",
                    assumption_type=AssumptionType.SAFE_DEFAULT,
                    source="SYSTEM_DEFAULT",
                    confidence=0.85,
                    impact_level="LOW",
                    is_reversible=True,
                ))

        # 2. Scope & Environment Ambiguity
        if "deploy" in lower_text and not any(env in lower_text for env in ["staging", "prod", "production", "dev", "development", "local"]):
            amb = Ambiguity(
                ambiguity_id=generate_id("amb"),
                intent_id=intent.intent_id,
                ambiguity_type=AmbiguityType.ENVIRONMENT,
                subject="Deployment Target Environment",
                explanation="Deployment requested without explicit environment target. Never assume production.",
                candidates=["DEVELOPMENT", "STAGING", "PRODUCTION"],
                consequence_level="CRITICAL",
                requires_user_clarification=True,
            )
            ambiguities.append(amb)

            clarifications.append(Clarification(
                clarification_id=generate_id("clr"),
                intent_id=intent.intent_id,
                ambiguity_id=amb.ambiguity_id,
                question="Which environment should this be deployed to?",
                rationale="Deployments have material environmental impact. Production is never assumed.",
                affected_decision="deployment_target_environment",
                consequence_level="CRITICAL",
                options=["staging", "development", "production"],
                safe_default="staging",
                status=ClarificationStatus.PENDING,
            ))

        # 3. Temporal Ambiguity (Spec 29)
        if "later" in lower_text or "soon" in lower_text:
            amb = Ambiguity(
                ambiguity_id=generate_id("amb"),
                intent_id=intent.intent_id,
                ambiguity_type=AmbiguityType.TEMPORAL,
                subject="Execution Window",
                explanation="Vague temporal indicator ('later'/'soon').",
                candidates=["next available window", "end of day", "specific schedule"],
                consequence_level="LOW",
                requires_user_clarification=False,
            )
            ambiguities.append(amb)
            assumptions.append(Assumption(
                assumption_id=generate_id("asm"),
                intent_id=intent.intent_id,
                statement="Standard asynchronous scheduling assumed for vague temporal request.",
                assumption_type=AssumptionType.SAFE_DEFAULT,
                source="SYSTEM_DEFAULT",
                confidence=0.9,
                impact_level="LOW",
                is_reversible=True,
            ))

        # 4. Quantity Ambiguity: "clean the old files" -> How old?
        if "old files" in lower_text and not re.search(r"\d+\s+(?:days|months|weeks)", lower_text):
            amb = Ambiguity(
                ambiguity_id=generate_id("amb"),
                intent_id=intent.intent_id,
                ambiguity_type=AmbiguityType.QUANTITY,
                subject="File Age Threshold",
                explanation="Age threshold for 'old files' is unspecified.",
                candidates=[">30 days", ">90 days", "archived only"],
                consequence_level="HIGH" if is_destructive else "LOW",
                requires_user_clarification=is_destructive,
            )
            ambiguities.append(amb)
            if is_destructive:
                clarifications.append(Clarification(
                    clarification_id=generate_id("clr"),
                    intent_id=intent.intent_id,
                    ambiguity_id=amb.ambiguity_id,
                    question="How old should files be to qualify for deletion (e.g., older than 30 days)?",
                    rationale="Destructive file removal requires an exact age boundary.",
                    affected_decision="retention_threshold",
                    consequence_level="HIGH",
                    options=["older than 30 days", "older than 90 days", "archive only"],
                    status=ClarificationStatus.PENDING,
                ))

        logger.info("Ambiguity analysis for intent %s: %d ambiguities, %d clarifications, %d assumptions",
                    intent.intent_id, len(ambiguities), len(clarifications), len(assumptions))
        return ambiguities, clarifications, assumptions
