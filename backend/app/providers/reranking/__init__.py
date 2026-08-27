"""Reranker provider selection.

One place decides which reranker is active, from `RERANKER_PROVIDER`. Nothing
downstream imports a concrete provider, so a reranker can be swapped — or compared
in `evaluation/` — without touching retrieval.

`none` is a deliberate, explicit option rather than a silent fallback: it
preserves retrieval order and reports scores of 0.0, which sit below
MIN_EVIDENCE_SCORE, so an instance running without a reranker cannot keep
answering as though evidence had been confirmed.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, settings
from app.core.logging import get_logger
from app.providers.reranking.base import (
    NoOpReranker,
    RerankerError,
    RerankerProvider,
    RerankResult,
)
from app.providers.reranking.mock import MockRerankerProvider

logger = get_logger(__name__)


def build_reranker_provider(config: Settings) -> RerankerProvider:
    """Construct the reranker named by `config.RERANKER_PROVIDER`.

    Raises:
        RerankerError: the selected provider is missing a credential. Raised at
            startup rather than at the first user question.
    """
    provider = config.RERANKER_PROVIDER

    if provider == "none":
        logger.warning(
            "reranking is disabled; retrieval order is used unchanged and every "
            "candidate scores 0.0, which is below MIN_EVIDENCE_SCORE"
        )
        return NoOpReranker()

    if provider == "mock":
        logger.warning(
            "using the mock reranker; relevance ordering is lexical only and "
            "results must not be evaluated"
        )
        return MockRerankerProvider()

    if provider == "pending":
        from app.providers.reranking.pending import PendingRerankerProvider

        logger.warning(
            "using PENDING reranker — acts like mock but signals that "
            "real reranking (alibaba/gte-rerank-v2) is intended once "
            "credentials are available"
        )
        return PendingRerankerProvider(
            target_provider="alibaba",
            target_model=config.ALIBABA_RERANKER_MODEL,
        )

    if provider == "alibaba":
        if config.ALIBABA_RERANKER_API_KEY is None:
            raise RerankerError(
                "RERANKER_PROVIDER=alibaba requires ALIBABA_RERANKER_API_KEY. "
                "Set it, or use RERANKER_PROVIDER=pending for offline work."
            )

        from app.providers.reranking.alibaba import AlibabaRerankerProvider

        return AlibabaRerankerProvider(
            api_key=config.ALIBABA_RERANKER_API_KEY.get_secret_value(),
            model=config.ALIBABA_RERANKER_MODEL,
            base_url=config.ALIBABA_RERANKER_BASE_URL,
            timeout=config.RERANKER_TIMEOUT_SECONDS,
        )

    raise RerankerError(f"Unknown reranker provider: {provider!r}")


@lru_cache(maxsize=1)
def get_reranker_provider() -> RerankerProvider:
    """The process-wide reranker instance."""
    return build_reranker_provider(settings)


def reset_reranker_provider() -> None:
    """Drop the cached provider. For tests that swap configuration."""
    get_reranker_provider.cache_clear()


__all__ = [
    "MockRerankerProvider",
    "NoOpReranker",
    "RerankResult",
    "RerankerError",
    "RerankerProvider",
    "build_reranker_provider",
    "get_reranker_provider",
    "reset_reranker_provider",
]
