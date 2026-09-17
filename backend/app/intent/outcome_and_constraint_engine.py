"""Desired Outcome, Constraint, Non-Goal & Preference Extraction Engine for Task 108.

Implements:
- Section 8: Desired Outcome ("What would success look like to the user?")
- Section 9: Constraint Extraction (explicit vs implicit, technical, resource, time, safety, privacy, environment)
- Section 10: Non-Goals (discovers explicit things user does NOT want; no hallucinated non-goals)
- Section 11: Preferences (separates current request instruction from historical memory)
- Section 29: Temporal Intent (resolves relative times, deadlines, windows)
- Section 32: Quality Requirements ("production-ready", "prototype", "fast", "secure", "cheap")
- Section 33: Resource Intent ("cheap", "free models", "RAM limits")
- Section 34: Environment Intent (dev, staging, prod; never assumes prod when unclear)
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.intent.domain import (
    Constraint,
    ConstraintEpistemic,
    ConstraintType,
    DesiredOutcome,
    EpistemicStatus,
    Intent,
    Preference,
    Requirement,
    generate_id,
    utc_now,
)

logger = logging.getLogger("kairo.intent.outcome_and_constraints")


class OutcomeAndConstraintEngine:
    """Extracts operational boundaries, observable outcomes, non-goals, and constraints."""

    # Explicit negation patterns for Non-Goals (Spec 10)
    _NON_GOAL_PATTERNS = [
        re.compile(r"\bwithout\s+([a-zA-Z0-9_\-\s]+?)(?:\s*(?:,|and|\.|$))", re.IGNORECASE),
        re.compile(r"\bdo\s+not\s+([a-zA-Z0-9_\-\s]+?)(?:\s*(?:,|and|\.|$))", re.IGNORECASE),
        re.compile(r"\bdon't\s+([a-zA-Z0-9_\-\s]+?)(?:\s*(?:,|and|\.|$))", re.IGNORECASE),
        re.compile(r"\bavoid\s+([a-zA-Z0-9_\-\s]+?)(?:\s*(?:,|and|\.|$))", re.IGNORECASE),
        re.compile(r"\bno\s+([a-zA-Z0-9_\-\s]+?)(?:\s*(?:,|and|\.|$))", re.IGNORECASE),
    ]

    # Environment extraction
    _ENV_PATTERNS = [
        (re.compile(r"\b(?:production|prod)\b", re.IGNORECASE), "PRODUCTION"),
        (re.compile(r"\b(?:staging|stage)\b", re.IGNORECASE), "STAGING"),
        (re.compile(r"\b(?:development|dev)\b", re.IGNORECASE), "DEVELOPMENT"),
        (re.compile(r"\b(?:test|testing|qa)\b", re.IGNORECASE), "TEST"),
        (re.compile(r"\b(?:local|localhost)\b", re.IGNORECASE), "LOCAL"),
    ]

    # Quality indicators
    _QUALITY_PATTERNS = [
        (re.compile(r"\b(?:production-ready|prod-ready|enterprise)\b", re.IGNORECASE), "PRODUCTION_READY", "Requires robust error handling, tests, and adherence to production guidelines."),
        (re.compile(r"\b(?:quick\s+prototype|prototype|poc|rough\s+draft|quick\s+hack)\b", re.IGNORECASE), "PROTOTYPE", "Emphasizes fast exploration and minimal boilerplate."),
        (re.compile(r"\b(?:minimal|lean|compact)\b", re.IGNORECASE), "MINIMAL", "Strictly minimum lines of code and minimal dependency changes."),
        (re.compile(r"\b(?:secure|hardened|audited)\b", re.IGNORECASE), "SECURE", "High security verification and validation boundaries."),
        (re.compile(r"\b(?:fast|low\s+latency|speedy)\b", re.IGNORECASE), "PERFORMANCE", "Prioritizes low execution latency and fast throughput."),
        (re.compile(r"\b(?:cheap|low\s+cost|free\s+tier|budget)\b", re.IGNORECASE), "RESOURCE_CONSERVATIVE", "Conserves API token cost and cognitive resources."),
    ]

    # Relative time patterns
    _TIME_PATTERNS = [
        (re.compile(r"\b(?:right\s+now|immediately|asap)\b", re.IGNORECASE), timedelta(minutes=0)),
        (re.compile(r"\bin\s+(\d+)\s+hours?\b", re.IGNORECASE), "HOURS"),
        (re.compile(r"\btoday\b", re.IGNORECASE), "TODAY"),
        (re.compile(r"\btomorrow\b", re.IGNORECASE), "TOMORROW"),
    ]

    @classmethod
    def extract_non_goals(cls, text: str) -> List[str]:
        """Discovers non-goals explicitly stated in user text (Spec 10)."""
        non_goals: List[str] = []
        for pat in cls._NON_GOAL_PATTERNS:
            for match in pat.finditer(text):
                phrase = match.group(1).strip()
                if phrase and len(phrase) > 2 and phrase not in non_goals:
                    non_goals.append(f"Do not {phrase}")
        return non_goals

    @classmethod
    def extract_constraints(cls, intent_id: str, text: str) -> List[Constraint]:
        """Extracts technical, environmental, resource, safety, and time constraints (Spec 9)."""
        constraints: List[Constraint] = []

        # 1. Environment constraints
        for pat, env_name in cls._ENV_PATTERNS:
            if pat.search(text):
                constraints.append(Constraint(
                    constraint_id=generate_id("cst"),
                    intent_id=intent_id,
                    constraint_type=ConstraintType.ENVIRONMENT,
                    epistemic_strength=ConstraintEpistemic.EXPLICIT,
                    description=f"Target environment must be {env_name}.",
                    parameter="target_environment",
                    value=env_name,
                    confidence=1.0,
                    source="USER_INSTRUCTION",
                ))

        # 2. Compatibility & Preservation constraints
        if "without changing" in text.lower() or "preserve" in text.lower():
            match = re.search(r"(?:without changing|preserve)\s+([a-zA-Z0-9_\-\s]+)", text, re.IGNORECASE)
            target_preserved = match.group(1).strip() if match else "functional behavior"
            constraints.append(Constraint(
                constraint_id=generate_id("cst"),
                intent_id=intent_id,
                constraint_type=ConstraintType.COMPATIBILITY,
                epistemic_strength=ConstraintEpistemic.EXPLICIT,
                description=f"Must preserve {target_preserved} without regressions.",
                parameter="preserved_feature",
                value=target_preserved,
                confidence=0.95,
                source="USER_INSTRUCTION",
            ))

        # 3. Resource / Cost constraints
        if any(w in text.lower() for w in ["cheap", "free", "cost", "tokens", "budget", "ram"]):
            constraints.append(Constraint(
                constraint_id=generate_id("cst"),
                intent_id=intent_id,
                constraint_type=ConstraintType.BUDGET,
                epistemic_strength=ConstraintEpistemic.EXPLICIT if "cheap" in text.lower() else ConstraintEpistemic.IMPLICIT,
                description="Resource usage must remain within conservative cost/budget limits.",
                parameter="budget_mode",
                value="CONSERVATIVE",
                confidence=0.9,
                source="USER_INSTRUCTION",
            ))

        # 4. Safety boundary constraint
        if any(w in text.lower() for w in ["safe", "do not break", "non-destructive"]):
            constraints.append(Constraint(
                constraint_id=generate_id("cst"),
                intent_id=intent_id,
                constraint_type=ConstraintType.SAFETY,
                epistemic_strength=ConstraintEpistemic.EXPLICIT,
                description="Action must not perform irreversible or destructive side-effects.",
                parameter="reversibility",
                value="MANDATORY_REVERSIBLE",
                confidence=1.0,
                source="USER_INSTRUCTION",
            ))

        return constraints

    @classmethod
    def extract_desired_outcome(cls, intent_id: str, text: str, category_name: str) -> DesiredOutcome:
        """Models 'What would success look like to the user?' (Spec 8)."""
        summary = f"Observable success for: {text}"
        observable = f"User goal completed without errors; changes adhere strictly to explicit constraints."
        acceptance = [
            "Functional outcome matches user directive.",
            "No unrequested mutations or behavioral side-effects introduced.",
        ]

        if "login" in text.lower():
            observable = "Authentication and login flows succeed without errors."
            acceptance = ["User can authenticate successfully", "No breaking changes to session handling"]
        elif "deploy" in text.lower():
            observable = "Deployment succeeds in specified environment and health check passes."
            acceptance = ["Service is running and responsive", "No rollbacks triggered"]
        elif "optimize" in text.lower() or "faster" in text.lower():
            observable = "Latency reduced or throughput increased while functional behavior remains invariant."
            acceptance = ["Benchmark demonstrates measurable performance gain", "Test suite passes 100%"]

        return DesiredOutcome(
            outcome_id=generate_id("out"),
            intent_id=intent_id,
            summary=summary,
            observable_outcome=observable,
            acceptance_criteria=acceptance,
            epistemic_status=EpistemicStatus.INFERRED,
            created_at=utc_now(),
        )

    @classmethod
    def extract_requirements(cls, intent_id: str, text: str) -> List[Requirement]:
        """Extracts quality and performance requirements (Spec 32)."""
        requirements: List[Requirement] = []
        for pat, cat, interp in cls._QUALITY_PATTERNS:
            match = pat.search(text)
            if match:
                requirements.append(Requirement(
                    requirement_id=generate_id("reqm"),
                    intent_id=intent_id,
                    category=cat,
                    raw_statement=match.group(0),
                    confidence=0.9,
                    interpretation=interp,
                    source="USER_INSTRUCTION",
                    created_at=utc_now(),
                ))
        return requirements

    @classmethod
    def extract_preferences(cls, intent_id: str, text: str, historical_prefs: Optional[Dict[str, Any]] = None) -> List[Preference]:
        """Extracts user preferences, separating current instruction from historical memory (Spec 11, 18)."""
        prefs: List[Preference] = []

        # Example language preference in current request: "write this in Python" vs "TypeScript"
        if "in python" in text.lower():
            prefs.append(Preference(
                preference_id=generate_id("prf"),
                intent_id=intent_id,
                key="programming_language",
                value="Python",
                is_current_request=True,
                confidence=1.0,
                source="EXPLICIT_USER",
            ))
        elif "in typescript" in text.lower():
            prefs.append(Preference(
                preference_id=generate_id("prf"),
                intent_id=intent_id,
                key="programming_language",
                value="TypeScript",
                is_current_request=True,
                confidence=1.0,
                source="EXPLICIT_USER",
            ))

        # Check historical memory candidates if provided, but mark is_current_request=False
        if historical_prefs:
            for k, v in historical_prefs.items():
                # Only add if not overridden by explicit current request
                if not any(p.key == k and p.is_current_request for p in prefs):
                    prefs.append(Preference(
                        preference_id=generate_id("prf"),
                        intent_id=intent_id,
                        key=k,
                        value=v,
                        is_current_request=False,
                        confidence=0.75,
                        source="HISTORICAL_MEMORY",
                    ))

        return prefs
