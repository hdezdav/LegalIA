"""Embedding generation for ingestion.

Separated from storage on purpose (section 14 of the brief): this module turns
chunks into vectors and knows nothing about PostgreSQL, while `indexer.py` writes
rows and knows nothing about providers. That split is what allows a local batch
embed pass, a remote provider, or a future re-embed job to reuse the same code.

Two properties the indexer depends on:

* **Order is preserved.** `result[i]` is the vector for `chunks[i]`. A reordered
  batch would attach every embedding to the wrong chunk, and nothing downstream
  could detect it.
* **Partial success is never silent.** A failed batch raises; it does not return
  short. Half-embedded documents would be invisible to retrieval while looking
  ingested.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.providers.embeddings.base import EmbeddingError, EmbeddingProvider

logger = get_logger(__name__)


@dataclass(slots=True)
class EmbeddingBatchResult:
    """Vectors plus the model identity they were produced with.

    `model_id` travels with the vectors because retrieval filters on it: chunks
    embedded by a different model must be invisible to search rather than ranked
    against these by a cosine distance that means nothing across spaces.
    """

    vectors: list[list[float]]
    model_id: str
    dimension: int


class EmbeddingGenerator:
    """Embeds chunk texts through the configured provider."""

    def __init__(self, provider: EmbeddingProvider) -> None:
        self.provider = provider

    @property
    def model_id(self) -> str:
        return self.provider.model_id

    @property
    def dimension(self) -> int:
        return self.provider.dimension

    async def embed_chunks(self, texts: list[str]) -> EmbeddingBatchResult:
        """Embed chunk texts in input order.

        Raises:
            EmbeddingError: the provider failed, or returned a vector count or
                width that does not match the request. Both are treated as fatal:
                a document is either fully embedded or not ingested at all.
        """
        if not texts:
            return EmbeddingBatchResult([], self.provider.model_id, self.provider.dimension)

        vectors = await self.provider.embed_batch(texts)

        # The provider already validates its own response, but this is the last
        # point before vectors are bound to chunk rows, so the invariant that
        # matters most is re-checked here rather than assumed.
        if len(vectors) != len(texts):
            raise EmbeddingError(
                f"Embedding provider returned {len(vectors)} vectors for "
                f"{len(texts)} chunks; refusing to store a misaligned document"
            )

        expected = self.provider.dimension
        for position, vector in enumerate(vectors):
            if len(vector) != expected:
                raise EmbeddingError(
                    f"Chunk {position} received a {len(vector)}-dimensional vector, "
                    f"expected {expected}"
                )

        logger.info(
            "embedded chunks",
            extra={
                "chunk_count": len(texts),
                "embedding_model": self.provider.model_id,
                "embedding_dimension": expected,
            },
        )

        return EmbeddingBatchResult(
            vectors=vectors,
            model_id=self.provider.model_id,
            dimension=expected,
        )
