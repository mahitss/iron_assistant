"""Kairo Unified Multimodal Intelligence Layer (Task 30).

Provides unified reasoning over authorized TEXT, IMAGE, AUDIO, VIDEO, SCREEN CONTEXT, and DOCUMENTS
through one consistent request/context architecture.
"""

from app.multimodal.context import MultimodalContextBuilder, MultimodalContextPacket
from app.multimodal.events import MultimodalEventPublisher
from app.multimodal.limits import MultimodalLimitExceededError, MultimodalLimits
from app.multimodal.normalizer import MediaNormalizer
from app.multimodal.results import MultimodalResultBuilder
from app.multimodal.router import MultimodalModelRouter, MultimodalRoutingError
from app.multimodal.schemas import (
    Attachment,
    AudioContext,
    ModalityType,
    MultimodalErrorState,
    MultimodalEvidenceItem,
    MultimodalRequest,
    MultimodalResult,
    MultimodalStatus,
    ScreenContext,
)
from app.multimodal.security import (
    MultimodalSecurityError,
    MultimodalSecurityGate,
    PrivilegedModalityPermission,
)
from app.multimodal.service import MultimodalService, get_multimodal_service
from app.multimodal.validator import MediaValidator, MultimodalValidationError

__all__ = [
    "ModalityType",
    "MultimodalStatus",
    "MultimodalErrorState",
    "Attachment",
    "ScreenContext",
    "AudioContext",
    "MultimodalRequest",
    "MultimodalEvidenceItem",
    "MultimodalResult",
    "MultimodalLimits",
    "MultimodalLimitExceededError",
    "MediaValidator",
    "MultimodalValidationError",
    "MediaNormalizer",
    "MultimodalSecurityGate",
    "MultimodalSecurityError",
    "PrivilegedModalityPermission",
    "MultimodalModelRouter",
    "MultimodalRoutingError",
    "MultimodalContextPacket",
    "MultimodalContextBuilder",
    "MultimodalResultBuilder",
    "MultimodalEventPublisher",
    "MultimodalService",
    "get_multimodal_service",
]
