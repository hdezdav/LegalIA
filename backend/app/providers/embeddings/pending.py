"""Pending embedding provider — semantic embeddings intended but not yet available.

This is the "en gris" (grayed out) state: acts exactly like the mock provider for
development, but uses a distinct model_id ("pending/alibaba-text-embedding-v4-1024")
that signals the user's intent to use real semantic embeddings once credentials or
infrastructure are available.

Use this when:
- Alibaba/BGE credentials are not yet configured
- You want to continue developing other parts of the system (citations, verification,
  frontend) without blocking on embeddings
- You need a clear signal in health checks and logs that this is temporary

The corpus embedded with "pending" can coexist with "mock" chunks (different
model_ids prevent mixing), but both will need to be re-ingested when switching to
a real provider.
"""

from __future__ import annotations

from app.providers.embeddings.base import EmbeddingProvider
from app.providers.embeddings.mock import MockEmbeddingProvider


class PendingEmbeddingProvider(EmbeddingProvider):
    """Mock embeddings with a model_id that signals intent for real embeddings."""

    def __init__(
        self,
        dimension: int = 1024,
        target_provider: str = "alibaba",
        target_model: str = "text-embedding-v4",
    ) -> None:
        """
        Args:
            dimension: vector width, must match the target provider's dimension
            target_provider: which provider you intend to use (for the model_id)
            target_model: which model you intend to use (for the model_id)
        """
        self._mock = MockEmbeddingProvider(dimension=dimension)
        self._target_provider = target_provider
        self._target_model = target_model

    @property
    def dimension(self) -> int:
        return self._mock.dimension

    @property
    def model_id(self) -> str:
        # Distinct from both "mock/hashed-1024" and "alibaba/text-embedding-v4-1024"
        # so it's clear this is temporary, and chunks won't be mistakenly searched
        # when the real provider activates.
        return f"pending/{self._target_provider}-{self._target_model}-{self.dimension}"

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._mock.embed_batch(texts)
