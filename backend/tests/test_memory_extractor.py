"""Unit tests for MemoryExtractor: prompt generation, structured JSON parsing, and failure recovery."""

import json
from typing import AsyncIterator, List, Optional

import pytest

from app.memory.extractor import MemoryExtractor
from app.memory.schemas import MemoryType
from app.models.provider import ChatMessage, ModelProvider, ProviderAPIError, ProviderResponse
from app.models.registry import ModelCapability, ModelDefinition, ModelRegistry
from app.models.router import ModelRouter


class MockExtractionProvider(ModelProvider):
    """Mock provider returning scripted extraction responses."""

    def __init__(self, responses: Optional[List[str]] = None):
        self.responses = responses or ['{"candidates": []}']
        self.call_count = 0
        self.recorded_messages: List[List[ChatMessage]] = []
        self.recorded_models: List[str] = []
        self.should_raise: bool = False

    async def generate_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> ProviderResponse:
        self.recorded_messages.append(list(messages))
        self.recorded_models.append(model or "")
        if self.should_raise:
            raise ProviderAPIError("Extraction model timed out", status_code=504)

        text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return ProviderResponse(content=text, model=model or "mock/fast")

    async def stream_response(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        tools: Optional[List[dict]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        yield "not supported"


@pytest.fixture
def mock_router() -> ModelRouter:
    """Fixture providing a test router with FAST capability mapped."""
    reg = ModelRegistry()
    reg.register_model(
        ModelDefinition(
            id="google/gemini-2.0-flash-001",
            capabilities={ModelCapability.FAST, ModelCapability.GENERAL},
            priority=100,
        )
    )
    reg.register_model(
        ModelDefinition(
            id="openrouter/free",
            capabilities={ModelCapability.GENERAL},
            priority=10,
        )
    )
    return ModelRouter(registry=reg, default_model_id="openrouter/free")


@pytest.mark.asyncio
async def test_extractor_valid_structured_candidate(mock_router: ModelRouter):
    """Verify that a valid JSON candidate structure is parsed cleanly."""
    model_json = json.dumps({
        "candidates": [
            {
                "content": "The user prefers TypeScript over Python.",
                "memory_type": "preference",
                "importance": 0.85,
                "reason": "Explicit user language preference",
            }
        ]
    })
    provider = MockExtractionProvider([model_json])
    extractor = MemoryExtractor(provider=provider, router=mock_router, capability="fast")

    candidates = await extractor.extract_candidates(
        user_message="I really prefer TypeScript over Python.",
        assistant_response="Understood, I'll write TypeScript examples.",
    )

    assert len(candidates) == 1
    cand = candidates[0]
    assert cand.content == "The user prefers TypeScript over Python."
    assert cand.memory_type == MemoryType.PREFERENCE
    assert cand.importance == 0.85
    assert cand.reason == "Explicit user language preference"

    # Verify FAST capability model was selected
    assert provider.recorded_models[0] == "google/gemini-2.0-flash-001"


@pytest.mark.asyncio
async def test_extractor_empty_result(mock_router: ModelRouter):
    """Verify that an empty candidate list returns an empty list without error."""
    provider = MockExtractionProvider(['{"candidates": []}'])
    extractor = MemoryExtractor(provider=provider, router=mock_router)

    candidates = await extractor.extract_candidates(
        user_message="What is the weather like today?",
        assistant_response="I cannot check real-time weather.",
    )

    assert candidates == []


@pytest.mark.asyncio
async def test_extractor_malformed_json_resilience():
    """Verify that malformed JSON or plain conversational text returns empty list gracefully."""
    provider = MockExtractionProvider(["Sorry, I cannot produce JSON right now."])
    extractor = MemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates("Hello", "Hi there")
    assert candidates == []


@pytest.mark.asyncio
async def test_extractor_markdown_fenced_json():
    """Verify extractor properly extracts JSON wrapped in Markdown ```json fences."""
    fenced_output = (
        "Here is the extraction:\n```json\n"
        '{\n  "candidates": [\n'
        '    {"content": "The user is building Kairo.", "memory_type": "project", "importance": 0.9}\n'
        "  ]\n}\n```"
    )
    provider = MockExtractionProvider([fenced_output])
    extractor = MemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates("I am building Kairo.", "Awesome project!")
    assert len(candidates) == 1
    assert candidates[0].content == "The user is building Kairo."
    assert candidates[0].memory_type == MemoryType.PROJECT


@pytest.mark.asyncio
async def test_extractor_invalid_memory_type_rejected():
    """Verify that unknown/invalid memory types are discarded."""
    bad_type_json = json.dumps({
        "candidates": [
            {"content": "Valid content", "memory_type": "invalid_unknown_type", "importance": 0.5},
            {"content": "Durable fact", "memory_type": "fact", "importance": 0.6},
        ]
    })
    provider = MockExtractionProvider([bad_type_json])
    extractor = MemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates("Msg", "Resp")
    assert len(candidates) == 1
    assert candidates[0].content == "Durable fact"
    assert candidates[0].memory_type == MemoryType.FACT


@pytest.mark.asyncio
async def test_extractor_importance_clamped():
    """Verify that out-of-range importance values (e.g. 5.0 or -1.0) are clamped to [0.0, 1.0]."""
    out_of_bounds = json.dumps({
        "candidates": [
            {"content": "User likes blue.", "memory_type": "preference", "importance": 12.5},
            {"content": "User dislikes noise.", "memory_type": "preference", "importance": -5.0},
        ]
    })
    provider = MockExtractionProvider([out_of_bounds])
    extractor = MemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates("Blue/noise", "Resp")
    assert len(candidates) == 2
    assert candidates[0].importance == 1.0
    assert candidates[1].importance == 0.0


@pytest.mark.asyncio
async def test_extractor_provider_failure_returns_empty():
    """Verify that if model provider raises an exception, extractor recovers and returns []."""
    provider = MockExtractionProvider()
    provider.should_raise = True
    extractor = MemoryExtractor(provider=provider)

    candidates = await extractor.extract_candidates("Some input", "Some response")
    assert candidates == []
