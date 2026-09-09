"""Embedding generation, caching, and model versioning manager."""

import hashlib
import logging
import math
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger("kairo.knowledge.embeddings")


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding generation models."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate normalized vector embeddings for a list of text strings."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Underlying embedding model identifier."""
        pass


class DeterministicMockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic pseudo-embedding provider generating reproducible unit vectors from text hash."""

    def __init__(self, dimension: int = 1536) -> None:
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return f"kairo-mock-embed-v1-{self._dim}"

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            # Deterministic hash to seed vector
            h = hashlib.sha256(text.encode("utf-8")).digest()
            vec: list[float] = []
            for i in range(self._dim):
                byte_val = h[i % len(h)]
                val = ((byte_val + (i * 31)) % 1000) / 500.0 - 1.0
                vec.append(val)

            # L2 Normalize
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            results.append([x / norm for x in vec])
        return results


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI text-embedding-3-small / large embedding generator."""

    def __init__(self, model: str = "text-embedding-3-small", dimension: int = 1536) -> None:
        self._model = model
        self._dim = dimension
        self._fallback = DeterministicMockEmbeddingProvider(dimension)

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            logger.debug("OpenAI API key missing; falling back to deterministic mock embeddings.")
            return await self._fallback.embed_texts(texts)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)
            response = await client.embeddings.create(input=texts, model=self._model)
            return [item.embedding for item in response.data]
        except Exception as ex:
            logger.warning(f"OpenAI embedding generation failed: {ex}. Using deterministic fallback.")
            return await self._fallback.embed_texts(texts)


class EmbeddingManager:
    """Central embedding orchestrator supporting caching, code specialization, and multi-providers."""

    def __init__(
        self,
        provider: BaseEmbeddingProvider | None = None,
        cache_size: int = 10000,
    ) -> None:
        self.provider = provider or DeterministicMockEmbeddingProvider()
        self._cache: dict[str, list[float]] = {}
        self._cache_size = cache_size

    def _cache_key(self, text: str, prefix: str = "") -> str:
        combined = f"{self.provider.model_name}:{prefix}:{text}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string with cache lookup."""
        key = self._cache_key(text)
        if key in self._cache:
            return self._cache[key]

        embeddings = await self.provider.embed_texts([text])
        if embeddings:
            vec = embeddings[0]
            if len(self._cache) < self._cache_size:
                self._cache[key] = vec
            return vec
        return [0.0] * self.provider.dimension

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch embed multiple texts with cache optimization."""
        results: list[list[float] | None] = [None] * len(texts)
        missing_indices: list[int] = []
        missing_texts: list[str] = []

        for idx, text in enumerate(texts):
            key = self._cache_key(text)
            if key in self._cache:
                results[idx] = self._cache[key]
            else:
                missing_indices.append(idx)
                missing_texts.append(text)

        if missing_texts:
            new_embeddings = await self.provider.embed_texts(missing_texts)
            for idx, vec in zip(missing_indices, new_embeddings, strict=False):
                results[idx] = vec
                key = self._cache_key(texts[idx])
                if len(self._cache) < self._cache_size:
                    self._cache[key] = vec

        return [res or [0.0] * self.provider.dimension for res in results]

    async def embed_code(
        self,
        code: str,
        language: str = "python",
        file_path: str | None = None,
        symbol_name: str | None = None,
    ) -> list[float]:
        """Embed code snippet with contextual semantic prefix."""
        prefix = f"Language: {language}"
        if file_path:
            prefix += f" | File: {file_path}"
        if symbol_name:
            prefix += f" | Symbol: {symbol_name}"

        contextualized = f"{prefix}\n{code}"
        return await self.embed_text(contextualized)

    async def embed_query(self, query: str) -> list[float]:
        """Embed a search query."""
        return await self.embed_text(query)
