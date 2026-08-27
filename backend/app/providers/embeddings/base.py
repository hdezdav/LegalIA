"""Embedding provider interface.

Every provider returns vectors of a fixed dimension. The active provider and its
dimension are configuration, not constants: switching from Alibaba (1024) to a
future fine-tuned BGE (768) requires a config change, a re-embed pass, and a
migration to alter the vector column width — all explicit, never silent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector width this provider returns."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Stable identifier recorded on every chunk this provider embeds.

        Retrieval filters on it, so vectors produced by a different model are
        invisible to search rather than silently mixed in. Two embedding spaces
        compared with cosine distance produce meaningless rankings, and that
        failure is invisible without this guard.

        Must encode everything that changes the vector space: provider, model, and
        dimension.
        """

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning one vector per input.

        The order is preserved: `result[i]` is the embedding for `texts[i]`.

        Raises:
            EmbeddingError: the provider refused the request, a text was too long,
                or the API is unreachable.
        """

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query.

        Some providers distinguish query embeddings from document embeddings; this
        is the query path. The default delegates to `embed_batch` with a
        single-item list.
        """
        return (await self.embed_batch([text]))[0]


class EmbeddingError(Exception):
    """Raised when embedding fails."""
