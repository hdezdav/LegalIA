"""Pending reranker provider — reranking intended but not yet available.

This is the "en gris" (grayed out) state for reranking: acts exactly like the mock
reranker for development, but uses a distinct model_id ("pending/alibaba-gte-rerank-v2")
that signals the user's intent to use real reranking once credentials are available.

Use this when:
- Alibaba credentials are not yet configured
- You want to continue developing other parts of the system without blocking on reranking
- You need a clear signal in health checks and logs that this is temporary
"""

from __future__ import annotations

from app.providers.reranking.base import RerankerProvider, RerankResult
from app.providers.reranking.mock import MockRerankerProvider


class PendingRerankerProvider(RerankerProvider):
    """Mock reranker with a model_id that signals intent for real reranking."""

    def __init__(
        self,
        target_provider: str = "alibaba",
        target_model: str = "gte-rerank-v2",
    ) -> None:
        """
        Args:
            target_provider: which provider you intend to use (for the model_id)
            target_model: which model you intend to use (for the model_id)
        """
        self._mock = MockRerankerProvider()
        self._target_provider = target_provider
        self._target_model = target_model

    @property
    def model_id(self) -> str:
        # Distinct from both "mock/lexical-rank" and "alibaba/gte-rerank-v2"
        return f"pending/{self._target_provider}-{self._target_model}"

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[RerankResult]:
        return await self._mock.rerank(query, documents, top_n)
