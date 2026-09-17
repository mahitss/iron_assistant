"""Kairo Autonomous Cognitive Memory, Experience Consolidation & Lifelong Learning Fabric (Task 103)."""

from app.cognitive_memory.domain import (
    CognitiveMemoryItem,
    Experience,
    ExperienceSource,
    ExperienceTrust,
    FreshnessState,
    MemoryApplicationRecord,
    MemoryConflict,
    MemoryContextPack,
    MemoryErrorType,
    MemoryFeedbackRecord,
    MemoryLifecycleState,
    MemoryPattern,
    MemoryScope,
    MemorySnapshot,
    MemoryType,
)
from app.cognitive_memory.router import router
from app.cognitive_memory.service import (
    CognitiveMemoryService,
    get_cognitive_memory_service,
)

__all__ = [
    "router",
    "CognitiveMemoryItem",
    "Experience",
    "ExperienceSource",
    "ExperienceTrust",
    "FreshnessState",
    "MemoryApplicationRecord",
    "MemoryConflict",
    "MemoryContextPack",
    "MemoryErrorType",
    "MemoryFeedbackRecord",
    "MemoryLifecycleState",
    "MemoryPattern",
    "MemoryScope",
    "MemorySnapshot",
    "MemoryType",
    "CognitiveMemoryService",
    "get_cognitive_memory_service",
]
