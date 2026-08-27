"""Embedding provider selection.

One place decides which provider is active, from `EMBEDDING_PROVIDER`. Nothing
downstream imports a concrete provider, which is what makes the Alibaba/BGE
comparison in `evaluation/` possible without touching retrieval.

`get_embedding_provider()` is cached: a provider holds credentials and, for BGE, a
loaded model, so it must be a single instance per process.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, settings
from app.core.logging import get_logger
from app.providers.embeddings.base import EmbeddingError, EmbeddingProvider
from app.providers.embeddings.mock import MockEmbeddingProvider

logger = get_logger(__name__)


def build_embedding_provider(config: Settings) -> EmbeddingProvider:
    """Construct the provider named by `config.EMBEDDING_PROVIDER`.

    Raises:
        EmbeddingError: the selected provider is missing a credential or an
            optional dependency. Raised at startup rather than at the first user
            question, so a misconfiguration is a boot failure, not a runtime one.
    """
    provider = config.EMBEDDING_PROVIDER

    if provider == "mock":
        logger.warning(
            "using the mock embedding provider; retrieval quality is not "
            "meaningful and results must not be evaluated",
            extra={"embedding_dimension": config.MOCK_EMBEDDING_DIMENSION},
        )
        return MockEmbeddingProvider(dimension=config.MOCK_EMBEDDING_DIMENSION)

    if provider == "pending":
        from app.providers.embeddings.pending import PendingEmbeddingProvider

        logger.warning(
            "using PENDING embedding provider — acts like mock but signals that "
            "real semantic embeddings (alibaba/text-embedding-v4) are intended once "
            "credentials/infrastructure are available",
            extra={"embedding_dimension": config.ALIBABA_EMBEDDING_DIMENSION},
        )
        return PendingEmbeddingProvider(
            dimension=config.ALIBABA_EMBEDDING_DIMENSION,
            target_provider="alibaba",
            target_model=config.ALIBABA_EMBEDDING_MODEL,
        )

    if provider == "alibaba":
        if config.ALIBABA_API_KEY is None:
            raise EmbeddingError(
                "EMBEDDING_PROVIDER=alibaba requires ALIBABA_API_KEY. "
                "Set it, or use EMBEDDING_PROVIDER=pending for offline work."
            )

        from app.providers.embeddings.alibaba import AlibabaEmbeddingProvider

        return AlibabaEmbeddingProvider(
            api_key=config.ALIBABA_API_KEY.get_secret_value(),
            model=config.ALIBABA_EMBEDDING_MODEL,
            dimension=config.ALIBABA_EMBEDDING_DIMENSION,
            base_url=config.ALIBABA_BASE_URL,
            timeout=config.EMBEDDING_TIMEOUT_SECONDS,
            batch_size=config.EMBEDDING_BATCH_SIZE,
        )

    if provider == "bge":
        from app.providers.embeddings.bge import BGEEmbeddingProvider

        if not BGEEmbeddingProvider.is_available():
            raise EmbeddingError(
                "EMBEDDING_PROVIDER=bge requires the local-embeddings extra. "
                "Install backend/requirements-local-embeddings.txt, or use "
                "EMBEDDING_PROVIDER=alibaba."
            )

        return BGEEmbeddingProvider(
            model_path=config.BGE_MODEL_PATH,
            dimension=config.BGE_EMBEDDING_DIMENSION,
            batch_size=config.BGE_BATCH_SIZE,
        )

    # Unreachable while EMBEDDING_PROVIDER is a Literal, but an explicit failure
    # is better than falling through to None if that type is ever widened.
    raise EmbeddingError(f"Unknown embedding provider: {provider!r}")


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """The process-wide provider instance."""
    return build_embedding_provider(settings)


def reset_embedding_provider() -> None:
    """Drop the cached provider. For tests that swap configuration."""
    get_embedding_provider.cache_clear()


__all__ = [
    "EmbeddingError",
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "build_embedding_provider",
    "get_embedding_provider",
    "reset_embedding_provider",
]
