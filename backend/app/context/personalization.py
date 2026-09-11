"""AdaptivePersonalizationEngine: Safe operational preference learning and decay (Task 69)."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.context.universal_schemas import (
    AdaptivePreference,
    AdaptivePreferenceCreate,
    AdaptivePreferenceUpdate,
    PreferenceCategory,
    PreferenceConfidence,
    PreferenceSource,
)

logger = logging.getLogger("kairo.context.personalization")


class SensitiveProfilingForbiddenError(ValueError):
    """Raised when an attempt is made to infer or store sensitive personal attributes."""

    pass


class AdaptivePersonalizationEngine:
    """Manages explicit and inferred operational preferences with safe confidence calibration and decay."""

    PROHIBITED_SENSITIVE_KEYWORDS = {
        "political",
        "politics",
        "religion",
        "religious",
        "race",
        "racial",
        "ethnicity",
        "ethnic",
        "sexual",
        "sexuality",
        "health",
        "medical",
        "disease",
        "disability",
        "criminal",
        "arrest",
        "conviction",
    }

    def __init__(self) -> None:
        # In-memory store keyed by (tenant_id, user_id, preference_id)
        self._preferences: dict[str, AdaptivePreference] = {}

    def _validate_safety(self, category: str, key: str, value: Any) -> None:
        """Enforce zero sensitive personal attribute profiling policy."""
        text_to_check = f"{category} {key} {str(value)}".lower()
        for kw in self.PROHIBITED_SENSITIVE_KEYWORDS:
            if kw in text_to_check:
                logger.warning("Blocked sensitive profiling attempt matching keyword '%s'", kw)
                raise SensitiveProfilingForbiddenError(
                    f"Personalization prohibited: Sensitive personal attribute profiling for '{kw}' is forbidden."
                )

    def register_preference(
        self,
        payload: AdaptivePreferenceCreate,
    ) -> AdaptivePreference:
        """Register an explicit or inferred user operational preference."""
        self._validate_safety(payload.category.value, payload.key, payload.value)

        # Check if matching pref already exists for this tenant/user/cat/key
        existing = self.find_preference(payload.tenant_id, payload.user_id, payload.category, payload.key)
        now = datetime.now(UTC)

        if existing:
            # If incoming is explicit, it overwrites inferred
            if (
                payload.source == PreferenceSource.EXPLICIT_PREFERENCE
                or existing.source == PreferenceSource.INFERRED_PREFERENCE
            ):
                updated = existing.model_copy(
                    update={
                        "value": payload.value,
                        "source": payload.source,
                        "confidence": payload.confidence,
                        "confidence_score": payload.confidence_score,
                        "occurrences": existing.occurrences + 1,
                        "updated_at": now,
                        "last_confirmed_at": now,
                        "is_active": True,
                    }
                )
                self._preferences[updated.preference_id] = updated
                return updated
            else:
                # Existing is explicit, incoming is inferred -> explicit remains authoritative
                updated = existing.model_copy(
                    update={
                        "occurrences": existing.occurrences + 1,
                        "updated_at": now,
                    }
                )
                self._preferences[updated.preference_id] = updated
                return updated

        pref = AdaptivePreference(
            user_id=payload.user_id,
            tenant_id=payload.tenant_id,
            category=payload.category,
            key=payload.key,
            value=payload.value,
            source=payload.source,
            confidence=payload.confidence,
            confidence_score=payload.confidence_score,
            occurrences=1,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_confirmed_at=now if payload.source == PreferenceSource.EXPLICIT_PREFERENCE else None,
        )
        self._preferences[pref.preference_id] = pref
        return pref

    def find_preference(
        self,
        tenant_id: str,
        user_id: str,
        category: PreferenceCategory,
        key: str,
    ) -> AdaptivePreference | None:
        """Find active preference by tenant, user, category, and key."""
        for p in self._preferences.values():
            if (
                p.tenant_id == tenant_id
                and p.user_id == user_id
                and p.category == category
                and p.key == key
                and p.is_active
            ):
                return p
        return None

    def record_behavior_observation(
        self,
        tenant_id: str,
        user_id: str,
        category: PreferenceCategory,
        key: str,
        observed_value: Any,
    ) -> AdaptivePreference:
        """Observe user action and incrementally infer/strengthen or decay preference."""
        self._validate_safety(category.value, key, observed_value)
        existing = self.find_preference(tenant_id, user_id, category, key)
        now = datetime.now(UTC)

        if not existing:
            # First observation -> low confidence inferred preference
            return self.register_preference(
                AdaptivePreferenceCreate(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    category=category,
                    key=key,
                    value=observed_value,
                    source=PreferenceSource.INFERRED_PREFERENCE,
                    confidence=PreferenceConfidence.LOW,
                    confidence_score=0.40,
                )
            )

        if existing.source == PreferenceSource.EXPLICIT_PREFERENCE:
            # Explicit preference remains, increment occurrences
            updated = existing.model_copy(update={"occurrences": existing.occurrences + 1, "updated_at": now})
            self._preferences[updated.preference_id] = updated
            return updated

        # Inferred preference check
        if existing.value == observed_value:
            # Reinforce observation
            new_occurrences = existing.occurrences + 1
            new_score = min(0.85, existing.confidence_score + 0.10)
            new_conf = PreferenceConfidence.HIGH if new_score >= 0.75 else PreferenceConfidence.MEDIUM
            updated = existing.model_copy(
                update={
                    "occurrences": new_occurrences,
                    "confidence_score": round(new_score, 2),
                    "confidence": new_conf,
                    "updated_at": now,
                }
            )
            self._preferences[updated.preference_id] = updated
            return updated
        else:
            # Shift in behavior: decay confidence score of old value
            new_score = max(0.15, existing.confidence_score - 0.20)
            new_conf = PreferenceConfidence.LOW
            if new_score <= 0.20:
                # Decayed sufficiently to adopt the newly observed value
                updated = existing.model_copy(
                    update={
                        "value": observed_value,
                        "confidence_score": 0.40,
                        "confidence": PreferenceConfidence.LOW,
                        "occurrences": 1,
                        "updated_at": now,
                    }
                )
            else:
                updated = existing.model_copy(
                    update={
                        "confidence_score": round(new_score, 2),
                        "confidence": new_conf,
                        "updated_at": now,
                    }
                )
            self._preferences[updated.preference_id] = updated
            return updated

    def decay_inactive_preferences(
        self,
        tenant_id: str,
        user_id: str,
        inactivity_days: int = 30,
    ) -> int:
        """Decay inferred preferences that have not been observed or confirmed recently."""
        now = datetime.now(UTC)
        threshold = now - timedelta(days=inactivity_days)
        decayed_count = 0

        for pref_id, p in list(self._preferences.items()):
            if p.tenant_id == tenant_id and p.user_id == user_id and p.is_active:
                if p.source == PreferenceSource.INFERRED_PREFERENCE and p.updated_at < threshold:
                    new_score = max(0.10, p.confidence_score - 0.15)
                    new_conf = PreferenceConfidence.LOW
                    self._preferences[pref_id] = p.model_copy(
                        update={
                            "confidence_score": round(new_score, 2),
                            "confidence": new_conf,
                            "updated_at": now,
                        }
                    )
                    decayed_count += 1

        return decayed_count

    def get_preferences(
        self,
        tenant_id: str,
        user_id: str,
        category: PreferenceCategory | None = None,
        active_only: bool = True,
    ) -> list[AdaptivePreference]:
        """Fetch preferences filtered by tenant, user, and category."""
        results: list[AdaptivePreference] = []
        for p in self._preferences.values():
            if p.tenant_id == tenant_id and p.user_id == user_id:
                if active_only and not p.is_active:
                    continue
                if category and p.category != category:
                    continue
                results.append(p)
        return sorted(results, key=lambda x: x.confidence_score, reverse=True)

    def get_preference_by_id(
        self,
        tenant_id: str,
        preference_id: str,
    ) -> AdaptivePreference | None:
        """Fetch preference by ID enforcing tenant isolation."""
        p = self._preferences.get(preference_id)
        if p and p.tenant_id == tenant_id:
            return p
        return None

    def update_preference(
        self,
        tenant_id: str,
        preference_id: str,
        updates: AdaptivePreferenceUpdate,
    ) -> AdaptivePreference | None:
        """Update existing preference with safety check."""
        p = self.get_preference_by_id(tenant_id, preference_id)
        if not p:
            return None

        if updates.value is not None:
            self._validate_safety(p.category.value, p.key, updates.value)

        dump = updates.model_dump(exclude_unset=True)
        dump["updated_at"] = datetime.now(UTC)
        updated = p.model_copy(update=dump)
        self._preferences[preference_id] = updated
        return updated

    def delete_preference(
        self,
        tenant_id: str,
        preference_id: str,
    ) -> bool:
        """Deactivate/delete preference enforcing tenant isolation."""
        p = self.get_preference_by_id(tenant_id, preference_id)
        if not p:
            return False
        # Soft-delete by marking inactive
        self._preferences[preference_id] = p.model_copy(
            update={"is_active": False, "updated_at": datetime.now(UTC)}
        )
        return True
