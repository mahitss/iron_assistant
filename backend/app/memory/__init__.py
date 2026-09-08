"""Memory module for Kairo AI assistant."""

from .embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingError,
    EmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    get_configured_embedding_provider,
)
from .extractor import MemoryExtractor
from .models import Conversation, Memory, Message
from .policies import MemoryPolicy, PolicyDecision
from .repository import ConversationRepository, MemoryRepository
from .sanitizer import MemorySanitizer, UnsafeMemoryError
from .schemas import (
    ConversationContext,
    MemoryCandidate,
    MemoryCreate,
    MemoryExtractionResult,
    MemoryResponse,
    MemorySearchResult,
    MemoryType,
    MemoryUpdate,
)
from .service import MemoryService
from .session import SessionManager, get_default_session_manager

__all__ = [
    "Conversation",
    "ConversationContext",
    "ConversationRepository",
    "DeterministicEmbeddingProvider",
    "EmbeddingError",
    "EmbeddingProvider",
    "Memory",
    "MemoryCandidate",
    "MemoryCreate",
    "MemoryExtractionResult",
    "MemoryExtractor",
    "MemoryPolicy",
    "MemoryRepository",
    "MemoryResponse",
    "MemorySanitizer",
    "MemorySearchResult",
    "MemoryService",
    "MemoryType",
    "MemoryUpdate",
    "Message",
    "OpenAICompatibleEmbeddingProvider",
    "PolicyDecision",
    "SessionManager",
    "UnsafeMemoryError",
    "get_configured_embedding_provider",
    "get_default_session_manager",
]

