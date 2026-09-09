"""Data Access and Classification Controller for Kairo Governance (Task 36).

Enforces:
- 5-tier data classification (PUBLIC, INTERNAL, PRIVATE, SENSITIVE, RESTRICTED).
- Absolute denial of secrets in LLM context.
- Explicit authorization requirements for screen, microphone, and camera streams.
- Model and provider eligibility based on data classification.
"""

from typing import Any

from app.policy.schemas import (
    DataClassification,
    PolicyContext,
    PolicyDecisionType,
)


class DataAccessController:
    """Controls data scoping, secret segregation, and provider eligibility."""

    # Approved providers per data classification tier
    APPROVED_DATA_PROVIDERS: dict[DataClassification, set[str]] = {
        DataClassification.PUBLIC: {"openai", "anthropic", "google", "local", "groq", "ollama", "mistral", "aws_bedrock"},
        DataClassification.INTERNAL: {"openai", "anthropic", "google", "local", "aws_bedrock"},
        DataClassification.PRIVATE: {"google", "anthropic", "aws_bedrock", "local"},
        DataClassification.SENSITIVE: {"aws_bedrock", "local", "google"},
        DataClassification.RESTRICTED: {"local"},  # Restricted data only allowed on air-gapped / local enclaves
    }

    @classmethod
    def evaluate_data_access(cls, context: PolicyContext) -> tuple[PolicyDecisionType | None, str | None, dict[str, Any]]:
        """Evaluate data access constraints and model provider eligibility.

        Returns (Decision, Reason, allowed_scope_modifications).
        """
        data_scope = context.data_scope or {}
        action = (context.action or "").strip().lower()
        allowed_scope: dict[str, Any] = {}

        # 1. Secret Protection (Section 28)
        if data_scope.get("contains_secrets") is True or any(k in action for k in ("export_secrets", "read_private_key", "dump_env")):
            # If target is directed towards model context
            target_str = str(context.target or "").lower()
            if "prompt" in target_str or "llm" in target_str or context.provider_model is not None:
                return PolicyDecisionType.DENY, "Direct injection of raw secrets into model context is prohibited", {}

        # 2. Sensor access (Microphone & Camera) - Sections 30, 31
        if any(k in action for k in ("record_audio", "microphone_stream", "capture_mic")):
            if not data_scope.get("user_consent_granted"):
                return PolicyDecisionType.REQUIRE_CONFIRMATION, "Microphone access requires explicit human consent and presence confirmation", {}

        if any(k in action for k in ("record_video", "camera_stream", "capture_cam")):
            if not data_scope.get("user_consent_granted"):
                return PolicyDecisionType.REQUIRE_CONFIRMATION, "Camera stream access requires explicit human consent and presence confirmation", {}

        # 3. Screen access (Section 29)
        if "screen_record" in action or "screen_capture_continuous" in action:
            if not data_scope.get("user_consent_granted"):
                return PolicyDecisionType.REQUIRE_CONFIRMATION, "Continuous screen capture requires explicit user confirmation", {}

        # 4. Model Routing & Data Classification (Sections 77, 78, 79, 145, 146)
        raw_class = str(data_scope.get("classification", "INTERNAL")).upper()
        try:
            classification = DataClassification(raw_class)
        except ValueError:
            classification = DataClassification.INTERNAL

        if context.provider_model:
            provider = str(context.provider_model.get("provider", "")).lower()
            approved_providers = cls.APPROVED_DATA_PROVIDERS.get(classification, {"local"})

            if provider and provider not in approved_providers:
                return (
                    PolicyDecisionType.DENY,
                    f"Data classification '{classification.value}' cannot be sent to unapproved model provider '{provider}'",
                    {}
                )

        # 5. Bulk Export Controls (Section 73)
        if data_scope.get("bulk_export") is True:
            allowed_scope["max_export_records"] = data_scope.get("max_records", 500)
            if classification in (DataClassification.SENSITIVE, DataClassification.RESTRICTED):
                return PolicyDecisionType.REQUIRE_APPROVAL, f"Bulk export of {classification.value} data requires administrator approval", allowed_scope

        allowed_scope["classification"] = classification.value
        return None, None, allowed_scope
