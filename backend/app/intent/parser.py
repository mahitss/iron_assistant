"""Unified Intent Parser integrating normalization, classification, references, policies, and validation (Spec 2-10, 64-66, 100-110)."""

from datetime import UTC, datetime, timedelta
import logging
import re
from typing import Any
import uuid

from app.intent.ambiguity import AmbiguityAnalyzer
from app.intent.classifier import CommandClassifier
from app.intent.confidence import ConfidenceEstimator
from app.intent.context import TemporalContextResolver
from app.intent.normalizer import CommandNormalizer
from app.intent.policies import IntentPolicyEngine
from app.intent.references import ReferenceResolver
from app.intent.schemas import (
    AmbiguityLevel,
    AmbiguityReport,
    CommandAttachment,
    CommandSchema,
    IntentConstraints,
    IntentEntity,
    IntentErrorState,
    IntentRiskLevel,
    IntentSchema,
    IntentTarget,
    IntentType,
    ResolutionMethod,
)
from app.intent.validator import IntentValidator

logger = logging.getLogger("kairo.intent.parser")


class IntentParser:
    """Parses raw user commands into structured, validated IntentSchema instances."""

    # Environment extraction pattern
    ENV_PATTERN = re.compile(r"\b(production|prod|staging|stage|development|dev|test|testing|qa)\b", re.IGNORECASE)

    # Condition pattern: "if <condition>, <action>" or "<action> if <condition>"
    COND_PATTERN = re.compile(r"\bif\s+([^,]+?)(?:,\s*then\s*|\s*,\s*|\s+then\s+)(.+)$", re.IGNORECASE)

    # Sequence pattern: "<action 1>, then <action 2>"
    SEQ_PATTERN = re.compile(r"\b(.+?)\s+then\s+(.+)$", re.IGNORECASE)

    # Budget pattern: "keep it cheap", "budget <limit>"
    BUDGET_PATTERN = re.compile(r"\b(cheap|low\s+cost|budget\s+(\$?\d+))\b", re.IGNORECASE)

    # Time limit: "for X minutes"
    TIME_PATTERN = re.compile(r"\bfor\s+(\d+)\s+(minutes?|mins?|hours?)\b", re.IGNORECASE)

    @classmethod
    def parse_command(
        cls,
        raw_text: str,
        user_id: str,
        session_id: str | None = None,
        conversation_id: str | None = None,
        attachments: list[CommandAttachment] | None = None,
        source_interface: str = "WEB",
        project_hint: str | None = None,
        user_timezone: str = "UTC",
        active_task: dict[str, Any] | None = None,
        project_context: dict[str, Any] | None = None,
        recent_artifacts: list[dict[str, Any]] | None = None,
        clarification_response: str | None = None,
        clarification_attempts: int = 0,
    ) -> tuple[CommandSchema, IntentSchema]:
        """
        Main parsing pipeline:
        raw input -> normalization -> classification -> references & temporal ->
        constraints & conditions -> policies & risk -> ambiguity & validation -> structured Intent.
        """
        # 1. Normalize (Spec 6, 7)
        original_text, normalized_text = CommandNormalizer.normalize(raw_text)

        # If user provided a clarification response (Spec 48), merge with original command intent
        effective_text = normalized_text
        if clarification_response:
            effective_text = f"{normalized_text} ({clarification_response.strip()})"

        command_id = str(uuid.uuid4())
        intent_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        attachments = attachments or []
        att_dicts = [a.model_dump() for a in attachments]

        # 2. Extract Constraints, Negations, Conditions, Deadlines (Spec 100-110)
        hard_negations = IntentPolicyEngine.extract_negations_and_hard_constraints(effective_text)

        conditions: list[str] = []
        cond_match = cls.COND_PATTERN.search(effective_text)
        if cond_match:
            conditions.append(cond_match.group(1).strip())

        # Time deadline
        deadline: datetime | None = None
        time_match = cls.TIME_PATTERN.search(effective_text)
        if time_match:
            val = int(time_match.group(1))
            unit = time_match.group(2).lower()
            delta = timedelta(minutes=val) if "min" in unit else timedelta(hours=val)
            deadline = now + delta

        # Target Environment
        env_match = cls.ENV_PATTERN.search(effective_text)
        target_env = env_match.group(1).lower() if env_match else None
        if target_env in ("prod", "production"):
            target_env = "production"
        elif target_env in ("stage", "staging"):
            target_env = "staging"
        elif target_env in ("dev", "development"):
            target_env = "development"

        # Disallowed environments from negations
        disallowed_envs = []
        for neg in hard_negations:
            neg_l = neg.lower()
            if "prod" in neg_l:
                disallowed_envs.append("production")
            if "stage" in neg_l:
                disallowed_envs.append("staging")

        constraints = IntentConstraints(
            deadline=deadline,
            environment=target_env,
            disallowed_environments=disallowed_envs,
            hard_negations=hard_negations,
            conditions=conditions,
        )

        # 3. Classify (Spec 50, 51)
        intent_type = CommandClassifier.classify(effective_text, attachments=att_dicts)

        # 4. Resolve Temporal Context (Spec 18, 19)
        temp_kw, temp_start, temp_end = TemporalContextResolver.resolve_temporal_range(
            effective_text,
            user_timezone=user_timezone,
            now_dt=now,
        )

        # 5. Resolve References (Spec 11-17)
        resolved_refs, ambiguous_candidates, detected_refs = ReferenceResolver.resolve_references(
            text=effective_text,
            attachments=att_dicts,
            project_context=project_context,
            active_task=active_task,
            recent_artifacts=recent_artifacts,
        )

        # 6. Entity & Target Construction (Spec 24-29)
        entities: list[IntentEntity] = []
        target: IntentTarget | None = None
        resolution_methods: list[ResolutionMethod] = []

        # If user explicitly specified clarification_response, resolve target from it
        if clarification_response:
            target = IntentTarget(
                entity_type="clarified_resource",
                name=clarification_response.strip(),
                environment=target_env,
                scope=project_hint,
            )
            resolution_methods.append(ResolutionMethod.EXPLICIT)
            ambiguous_candidates = []  # cleared by clarification

        # Otherwise resolve from references or project hints
        elif resolved_refs.get("this"):
            r = resolved_refs["this"]
            target = IntentTarget(
                entity_type=r.get("type", "attachment"),
                stable_entity_id=r.get("id"),
                name=r.get("name", "attachment"),
                scope=project_hint,
                environment=target_env,
            )
            resolution_methods.append(r.get("method", ResolutionMethod.EXPLICIT))

        elif resolved_refs.get("the_repo"):
            r = resolved_refs["the_repo"]
            target = IntentTarget(
                entity_type="repository",
                stable_entity_id=r.get("id"),
                name=r.get("name", "repo"),
                scope=project_hint,
                environment=target_env,
            )
            resolution_methods.append(r.get("method", ResolutionMethod.CONTEXT))

        elif resolved_refs.get("the_task") or resolved_refs.get("it"):
            ref_val = resolved_refs.get("the_task") or resolved_refs.get("it")
            if ref_val:
                target = IntentTarget(
                    entity_type=ref_val.get("type", "task"),
                    stable_entity_id=ref_val.get("id"),
                    name=ref_val.get("name", "task"),
                    scope=project_hint,
                    environment=target_env,
                )
                resolution_methods.append(ref_val.get("method", ResolutionMethod.CONTEXT))

        elif project_context and project_context.get("name"):
            repos = project_context.get("repositories", [])
            # If command implies deployment, build, or task and project has multiple repositories, flag ambiguity (Spec 143)
            if len(repos) > 1 and any(kw in effective_text.lower() for kw in ("deploy", "ci", "test", "build", "repo")):
                target = None
                ambiguous_candidates.append({
                    "reference": "repository",
                    "candidates": repos,
                    "reason": f"Project '{project_context.get('name')}' contains multiple repositories: {', '.join(repos)}. Which one?",
                })
            else:
                target = IntentTarget(
                    entity_type="project",
                    stable_entity_id=project_context.get("id"),
                    name=project_context.get("name"),
                    scope=project_hint,
                    environment=target_env,
                )
                resolution_methods.append(ResolutionMethod.CONTEXT)

        # 7. Evaluate Risk (Spec 38)
        is_destructive = intent_type in (IntentType.DELETE, IntentType.CONTROL)
        risk_level = IntentPolicyEngine.evaluate_risk(
            intent_type=intent_type,
            target_name=target.name if target else None,
            environment=target_env,
            is_destructive=is_destructive,
        )

        # 8. Ambiguity Analysis (Spec 39-47)
        missing_params = []
        if intent_type in (IntentType.DELETE, IntentType.CONTROL) and not target:
            missing_params.append("target_resource")
        if intent_type == IntentType.REMIND and not (temp_kw or "remind" in effective_text):
            missing_params.append("reminder_details")

        ambiguity_report = AmbiguityAnalyzer.analyze(
            intent_type=intent_type,
            risk_level=risk_level,
            ambiguous_candidates=ambiguous_candidates,
            missing_params=missing_params,
            target=target.model_dump() if target else None,
            clarification_attempts=clarification_attempts,
        )

        # 9. Estimate Confidence (Spec 37)
        confidence = ConfidenceEstimator.estimate(
            resolution_methods=resolution_methods,
            has_ambiguity=ambiguity_report.ambiguous,
            missing_params_count=len(ambiguity_report.missing_information),
        )

        # 10. Validate Intent & Determine Execution Status (Spec 121)
        is_valid, error_state, err_msg = IntentValidator.validate_intent(
            intent_type=intent_type,
            target=target,
            constraints=constraints,
            authenticated_user_id=user_id,
            is_ambiguous=ambiguity_report.ambiguous,
        )

        status = error_state.value if not is_valid else "READY"
        if ambiguity_report.ambiguous:
            status = IntentErrorState.WAITING_USER.value

        # Construct CommandSchema and IntentSchema
        command_schema = CommandSchema(
            command_id=command_id,
            user_id=user_id,
            session_id=session_id,
            conversation_id=conversation_id,
            text=normalized_text,
            original_text=original_text,
            attachments=attachments,
            source_interface=source_interface,
            project_hint=project_hint,
            created_at=now,
        )

        intent_schema = IntentSchema(
            intent_id=intent_id,
            source_command_id=command_id,
            type=intent_type,
            objective=normalized_text,
            entities=entities,
            references=detected_refs,
            target=target,
            constraints=constraints,
            requested_action=intent_type.value,
            confidence=confidence,
            ambiguity=ambiguity_report,
            risk=risk_level,
            status=status,
            next_action="clarify" if status == IntentErrorState.WAITING_USER.value else "execute",
            created_at=now,
        )

        return command_schema, intent_schema
