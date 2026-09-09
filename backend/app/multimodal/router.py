"""Multimodal Model Router with capability matching, cost tracking, and fallback (Specs 28-32)."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Set

from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry
from app.models.router import ModelRouter
from app.multimodal.schemas import ModalityType, MultimodalErrorState

logger = logging.getLogger("kairo.multimodal.router")


class MultimodalRoutingError(Exception):
    """Raised when routing fails to find a capable model."""

    def __init__(self, error_code: MultimodalErrorState, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


@dataclass
class MultimodalUsageMetrics:
    """Resource and cost tracking for multimodal inferences (Spec 32)."""

    image_count: int = 0
    audio_duration_seconds: float = 0.0
    video_frames: int = 0
    video_duration_seconds: float = 0.0
    document_chunk_count: int = 0
    estimated_tokens: int = 0


class MultimodalModelRouter:
    """Selects and validates models declaring required multimodal capabilities."""

    def __init__(self, registry: ModelRegistry, base_router: ModelRouter | None = None) -> None:
        self.registry = registry
        self.base_router = base_router or ModelRouter(registry)

    def resolve_model_for_modalities(
        self,
        required_modalities: set[ModalityType],
        needs_structured_output: bool = False,
        preferred_model_id: str | None = None,
    ) -> ModelDefinition:
        """Find an enabled model that declares all required capabilities.

        Never silently routes visual or audio requests to text-only models (Spec 29).
        """
        # Map ModalityType to ModelCapability
        required_caps: set[ModelCapability] = set()

        if ModalityType.TEXT in required_modalities or not required_modalities:
            required_caps.add(ModelCapability.GENERAL)

        if ModalityType.IMAGE in required_modalities or ModalityType.SCREEN in required_modalities:
            # Check VISION or IMAGE capability
            required_caps.add(ModelCapability.VISION)

        if ModalityType.AUDIO in required_modalities:
            required_caps.add(ModelCapability.AUDIO)

        if ModalityType.VIDEO in required_modalities:
            required_caps.add(ModelCapability.VIDEO)

        if ModalityType.DOCUMENT in required_modalities:
            required_caps.add(ModelCapability.DOCUMENT)

        if needs_structured_output:
            required_caps.add(ModelCapability.STRUCTURED_OUTPUT)

        # 1. Check if preferred model is compatible and enabled
        if preferred_model_id:
            candidate = self.registry.get_model(preferred_model_id)
            if candidate and candidate.enabled and self._model_satisfies_caps(candidate, required_caps):
                return candidate

        # 2. Search registered models for full capability match
        candidates = self.registry.list_models(enabled_only=True)
        matching_models = [m for m in candidates if self._model_satisfies_caps(m, required_caps)]

        if matching_models:
            # Sort by priority descending
            matching_models.sort(key=lambda m: m.priority, reverse=True)
            return matching_models[0]

        # 3. Fallback compatibility check
        # If AUDIO or VIDEO is requested but can be preprocessed to text (STT / frame extraction),
        # check if a vision/general model can handle the derived data
        if ModalityType.VIDEO in required_modalities or ModalityType.AUDIO in required_modalities:
            # Fallback model for derived text/vision
            sub_caps = {c for c in required_caps if c not in (ModelCapability.AUDIO, ModelCapability.VIDEO)}
            sub_caps.add(ModelCapability.VISION)
            fallback_models = [m for m in candidates if self._model_satisfies_caps(m, sub_caps)]
            if fallback_models:
                fallback_models.sort(key=lambda m: m.priority, reverse=True)
                return fallback_models[0]

        # 4. If no compatible model exists, return CAPABILITY_UNAVAILABLE error (Spec 29)
        cap_names = [c.value for c in required_caps]
        raise MultimodalRoutingError(
            MultimodalErrorState.CAPABILITY_UNAVAILABLE,
            f"No enabled model found supporting required capabilities: {', '.join(cap_names)}. "
            f"Cannot route multimodal media to text-only model without compatible processing pipeline.",
        )

    def _model_satisfies_caps(self, model: ModelDefinition, required_caps: set[ModelCapability]) -> bool:
        """Check if model satisfies all required capabilities (with vision/image aliasing)."""
        caps = model.capabilities
        for req in required_caps:
            if req == ModelCapability.VISION:
                if ModelCapability.VISION not in caps and ModelCapability.IMAGE not in caps:
                    return False
            elif req == ModelCapability.IMAGE:
                if ModelCapability.IMAGE not in caps and ModelCapability.VISION not in caps:
                    return False
            elif req not in caps:
                return False
        return True

    def calculate_usage(
        self,
        images: int = 0,
        audio_seconds: float = 0.0,
        video_seconds: float = 0.0,
        video_frames: int = 0,
        document_chunks: int = 0,
        prompt_chars: int = 0,
    ) -> MultimodalUsageMetrics:
        """Estimate tokens and track resource usage for billing/observability (Spec 32)."""
        # Token approximations:
        # ~85 tokens per image thumbnail/tile
        # ~100 tokens per minute of audio transcript
        # ~85 tokens per video keyframe
        # ~200 tokens per document chunk
        # ~0.25 tokens per character of text
        est_tokens = int(
            (images * 85)
            + (audio_seconds / 60.0 * 100)
            + (video_frames * 85)
            + (document_chunks * 200)
            + (prompt_chars * 0.25)
        )
        return MultimodalUsageMetrics(
            image_count=images,
            audio_duration_seconds=round(audio_seconds, 2),
            video_frames=video_frames,
            video_duration_seconds=round(video_seconds, 2),
            document_chunk_count=document_chunks,
            estimated_tokens=est_tokens,
        )
