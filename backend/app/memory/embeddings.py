"""Embedding provider abstraction and implementations for semantic search."""

import hashlib
import math
from typing import Protocol, runtime_checkable

import httpx

from app.core.config import get_settings


class EmbeddingError(Exception):
    """Base exception for embedding generation failures."""


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    dimension: int

    async def embed(self, text: str) -> list[float]:
        """Generate a dense embedding vector for a single text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate dense embedding vectors for a batch of texts."""
        ...


class DeterministicEmbeddingProvider:
    """Deterministic, reproducible embedding provider for testing and isolated environments.

    Projects text tokens into a unit-normalized vector using stable hashing.
    Does NOT use pseudo-random numbers, ensuring repeatable semantic similarity tests.
    """

    def __init__(self, dimension: int = 1536) -> None:
        self.dimension = dimension

    async def embed(self, text: str) -> list[float]:
        """Generate a deterministic unit-normalized vector for the text."""
        words = text.lower().strip().split()
        if not words:
            return [0.0] * self.dimension

        vec = [0.0] * self.dimension
        for word in words:
            # Map word to indices using sha256 chunks
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            for i in range(0, min(16, len(digest) - 1), 2):
                idx = int.from_bytes(digest[i : i + 2], "big") % self.dimension
                val = (digest[i] - 128) / 128.0
                vec[idx] += val

        # Normalize vector to unit length (L2 norm)
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            return [x / norm for x in vec]
        return vec

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate deterministic embeddings for multiple texts."""
        return [await self.embed(t) for t in texts]


class OpenAICompatibleEmbeddingProvider:
    """Generates embeddings using an OpenAI-compatible /v1/embeddings endpoint."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "text-embedding-3-small",
        dimension: int = 1536,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dimension = dimension
        self._client = client

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(timeout=30.0)

    async def embed(self, text: str) -> list[float]:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingError("Embedding API key is not configured.")

        client = self._get_client()
        should_close = self._client is None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model,
        }

        try:
            resp = await client.post(f"{self.base_url}/embeddings", json=payload, headers=headers)
            if resp.status_code != 200:
                raise EmbeddingError(f"Embedding API returned error (status {resp.status_code}): {resp.text[:200]}")

            data = resp.json()
            items = data.get("data", [])
            # Sort items by index if returned
            sorted_items = sorted(items, key=lambda x: x.get("index", 0))
            return [item["embedding"] for item in sorted_items]
        except httpx.RequestError as exc:
            raise EmbeddingError(f"Network error communicating with embedding provider: {exc}")
        finally:
            if should_close:
                await client.aclose()


def get_configured_embedding_provider() -> EmbeddingProvider | None:
    """Resolve and return configured embedding provider based on application settings."""
    settings = get_settings()
    provider_type = (settings.KAIRO_EMBEDDING_PROVIDER or "").strip().lower()

    if not provider_type:
        return None

    if provider_type in ("mock", "deterministic", "test"):
        return DeterministicEmbeddingProvider(dimension=1536)

    if provider_type in ("openai", "openrouter"):
        api_key = settings.openrouter_api_key_str
        base_url = settings.OPENROUTER_BASE_URL if provider_type == "openrouter" else "https://api.openai.com/v1"
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.KAIRO_EMBEDDING_MODEL,
            dimension=1536,
        )

    return None
