"""Embedding provider tests.

No external API is called. The Alibaba provider is exercised through an injected
`httpx` transport, which covers the request it builds, the response contract it
expects, and every failure mapping — the parts that would otherwise only be
verified by a live call.
"""

from __future__ import annotations

import json
import math

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.providers.embeddings import build_embedding_provider
from app.providers.embeddings.alibaba import AlibabaEmbeddingProvider
from app.providers.embeddings.base import EmbeddingError
from app.providers.embeddings.mock import MockEmbeddingProvider


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "ENVIRONMENT": "test",
        "EMBEDDING_PROVIDER": "mock",
        "RERANKER_PROVIDER": "mock",
        "_env_file": None,
    }
    return Settings(**(base | overrides))  # type: ignore[arg-type]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


# --- Mock provider ----------------------------------------------------------


async def test_mock_returns_one_vector_per_input() -> None:
    provider = MockEmbeddingProvider(dimension=64)

    vectors = await provider.embed_batch(["uno", "dos", "tres"])

    assert len(vectors) == 3
    assert all(len(vector) == 64 for vector in vectors)


async def test_mock_is_deterministic() -> None:
    """Retrieval tests must be reproducible across runs."""
    provider = MockEmbeddingProvider(dimension=64)

    first = await provider.embed_batch(["responsabilidad patrimonial"])
    second = await provider.embed_batch(["responsabilidad patrimonial"])

    assert first == second


async def test_mock_vectors_are_unit_length() -> None:
    """pgvector cosine distance assumes a usable norm; zero vectors are undefined."""
    provider = MockEmbeddingProvider(dimension=64)

    (vector,) = await provider.embed_batch(["artículo 90 de la Constitución"])

    assert math.isclose(math.sqrt(sum(c * c for c in vector)), 1.0, rel_tol=1e-9)


async def test_mock_handles_text_with_no_tokens() -> None:
    """Punctuation-only text must still produce a valid unit vector."""
    provider = MockEmbeddingProvider(dimension=16)

    (vector,) = await provider.embed_batch(["...---..."])

    assert math.isclose(math.sqrt(sum(c * c for c in vector)), 1.0, rel_tol=1e-9)


async def test_mock_ranks_shared_vocabulary_above_unrelated_text() -> None:
    """The one geometric property retrieval tests may rely on.

    Not semantics: the mock cannot match paraphrases, and must never be used to
    judge retrieval quality.
    """
    provider = MockEmbeddingProvider(dimension=512)

    query, related, unrelated = await provider.embed_batch(
        [
            "responsabilidad patrimonial del Estado",
            "El Estado responderá patrimonialmente por los daños antijurídicos",
            "Todo trabajador tiene derecho a vacaciones remuneradas",
        ]
    )

    assert _cosine(query, related) > _cosine(query, unrelated)


async def test_mock_embed_query_matches_embed_batch() -> None:
    provider = MockEmbeddingProvider(dimension=32)

    single = await provider.embed_query("consulta")
    (batched,) = await provider.embed_batch(["consulta"])

    assert single == batched


def test_mock_rejects_a_non_positive_dimension() -> None:
    with pytest.raises(ValueError, match="positive"):
        MockEmbeddingProvider(dimension=0)


# --- Alibaba provider: stubbed transport ------------------------------------


def _stub(handler) -> httpx.MockTransport:  # type: ignore[no-untyped-def]
    return httpx.MockTransport(handler)


def _vector_response(request: httpx.Request, dimension: int = 4) -> httpx.Response:
    body = json.loads(request.content)
    inputs = body["input"]
    return httpx.Response(
        200,
        json={
            "data": [
                {"index": i, "embedding": [0.5] * dimension}
                for i in range(len(inputs))
            ],
            "model": body["model"],
            "usage": {"total_tokens": 10},
        },
    )


def _provider(handler, **overrides: object) -> AlibabaEmbeddingProvider:  # type: ignore[no-untyped-def]
    kwargs: dict[str, object] = {
        "api_key": "test-key",
        "model": "text-embedding-v4",
        "dimension": 4,
        "base_url": "https://example.test/compatible-mode/v1",
        "transport": _stub(handler),
    }
    return AlibabaEmbeddingProvider(**(kwargs | overrides))  # type: ignore[arg-type]


async def test_alibaba_sends_the_expected_request() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return _vector_response(request)

    provider = _provider(handler)
    await provider.embed_batch(["texto"])

    assert seen["url"] == "https://example.test/compatible-mode/v1/embeddings"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"] == {
        "model": "text-embedding-v4",
        "input": ["texto"],
        "encoding_format": "float",
        "dimensions": 4,
    }


async def test_alibaba_returns_vectors_in_input_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # Deliberately out of order: the provider must sort by `index`, because a
        # silently reordered batch would attach every embedding to the wrong chunk.
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [0.2, 0.2, 0.2, 0.2]},
                    {"index": 0, "embedding": [0.1, 0.1, 0.1, 0.1]},
                ]
            },
        )

    provider = _provider(handler)
    vectors = await provider.embed_batch(["primero", "segundo"])

    assert vectors[0][0] == pytest.approx(0.1)
    assert vectors[1][0] == pytest.approx(0.2)


async def test_alibaba_splits_oversized_batches() -> None:
    """The API rejects a batch over its limit rather than truncating it."""
    batch_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        batch_sizes.append(len(json.loads(request.content)["input"]))
        return _vector_response(request)

    provider = _provider(handler)
    vectors = await provider.embed_batch([f"chunk {i}" for i in range(25)])

    assert len(vectors) == 25
    assert max(batch_sizes) <= 10
    assert sum(batch_sizes) == 25


async def test_alibaba_rejects_a_dimension_mismatch() -> None:
    """A width that disagrees with configuration cannot be stored: the column is
    fixed-width, so this must fail loudly rather than be truncated."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"data": [{"index": 0, "embedding": [0.1] * 1536}]}
        )

    provider = _provider(handler)

    with pytest.raises(EmbeddingError, match="dimension 1536"):
        await provider.embed_batch(["texto"])


async def test_alibaba_rejects_a_short_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"index": 0, "embedding": [0.1] * 4}]})

    provider = _provider(handler)

    with pytest.raises(EmbeddingError, match="1 vectors for 2 inputs"):
        await provider.embed_batch(["uno", "dos"])


async def test_alibaba_rejects_empty_input() -> None:
    provider = _provider(_vector_response)

    with pytest.raises(EmbeddingError, match="empty text"):
        await provider.embed_batch(["válido", "   "])


async def test_alibaba_returns_nothing_for_no_input() -> None:
    """No request should be issued at all."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call expected for an empty batch")

    provider = _provider(handler)

    assert await provider.embed_batch([]) == []


async def test_alibaba_surfaces_a_credential_error_without_retrying() -> None:
    """401 is terminal: retrying a rejected key only burns the rate limit."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    provider = _provider(handler)

    with pytest.raises(EmbeddingError, match="credentials"):
        await provider.embed_batch(["texto"])
    assert attempts == 1


async def test_alibaba_surfaces_an_unknown_model_without_retrying() -> None:
    """The failure mode observed against a workspace with no embedding model
    deployed: HTTP 404 `Model not exist`. Terminal, not transient."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            404, json={"error": {"message": "Model not exist.", "code": "model_not_found"}}
        )

    provider = _provider(handler)

    with pytest.raises(EmbeddingError, match="HTTP 404"):
        await provider.embed_batch(["texto"])
    assert attempts == 1


async def test_alibaba_retries_a_rate_limit_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        return _vector_response(request)

    provider = _provider(handler)
    vectors = await provider.embed_batch(["texto"])

    assert attempts == 2
    assert len(vectors) == 1


async def test_alibaba_retries_a_server_error() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503)
        return _vector_response(request)

    provider = _provider(handler)
    await provider.embed_batch(["texto"])

    assert attempts == 3


async def test_alibaba_gives_up_after_the_retry_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    provider = _provider(handler)

    with pytest.raises(EmbeddingError, match="server error"):
        await provider.embed_batch(["texto"])


async def test_alibaba_error_never_echoes_the_submitted_text() -> None:
    """A provider error must not quote the input: for a private document that
    would put its content into logs."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"error": {"message": "invalid input: CLAUSULA CONFIDENCIAL"}}
        )

    provider = _provider(handler)

    with pytest.raises(EmbeddingError) as exc_info:
        await provider.embed_batch(["CLAUSULA CONFIDENCIAL"])

    assert "CONFIDENCIAL" not in str(exc_info.value)


def test_alibaba_requires_an_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        AlibabaEmbeddingProvider(api_key="")


# --- Factory ----------------------------------------------------------------


def test_factory_builds_the_mock_provider_at_its_configured_dimension() -> None:
    provider = build_embedding_provider(
        _settings(EMBEDDING_PROVIDER="mock", MOCK_EMBEDDING_DIMENSION=256)
    )

    assert isinstance(provider, MockEmbeddingProvider)
    assert provider.dimension == 256


def test_factory_builds_alibaba_from_configuration() -> None:
    provider = build_embedding_provider(
        _settings(
            EMBEDDING_PROVIDER="alibaba",
            ALIBABA_API_KEY=SecretStr("key"),
            ALIBABA_EMBEDDING_MODEL="text-embedding-v4",
            ALIBABA_EMBEDDING_DIMENSION=1024,
            ALIBABA_BASE_URL="https://workspace.test/compatible-mode/v1",
        )
    )

    assert isinstance(provider, AlibabaEmbeddingProvider)
    assert provider.dimension == 1024
    # A dedicated workspace is served from its own host, so this must not be
    # pinned to the public endpoint.
    assert provider.base_url == "https://workspace.test/compatible-mode/v1"


def test_factory_fails_fast_when_the_selected_provider_has_no_key() -> None:
    """Raised at startup, not at the first user question."""
    with pytest.raises(EmbeddingError, match="ALIBABA_API_KEY"):
        build_embedding_provider(
            _settings(EMBEDDING_PROVIDER="alibaba", ALIBABA_API_KEY=None)
        )


def test_factory_dimension_matches_settings_for_every_provider() -> None:
    """The DB column is created from `settings.embedding_dimension`; a provider
    that disagreed would write vectors the column cannot hold."""
    config = _settings(EMBEDDING_PROVIDER="mock", MOCK_EMBEDDING_DIMENSION=128)

    assert build_embedding_provider(config).dimension == config.embedding_dimension
