"""Reranker provider tests.

No external API is called. The Alibaba provider is exercised through an injected
`httpx` transport, which covers the native DashScope request it builds, the
response contract it expects, and every failure mapping.

The invariant most worth protecting here: scores are re-associated by the
provider's returned *index*, never by position. Getting that wrong attaches a
score to the wrong passage and produces a citation pointing at text the model
never saw.
"""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.providers.reranking import build_reranker_provider
from app.providers.reranking.alibaba import MAX_DOCUMENTS, AlibabaRerankerProvider
from app.providers.reranking.base import NoOpReranker, RerankerError
from app.providers.reranking.mock import MockRerankerProvider

RESPONSABILIDAD = (
    "El Estado responderá patrimonialmente por los daños antijurídicos que le "
    "sean imputables, causados por la acción o la omisión de las autoridades."
)
VACACIONES = (
    "Todo trabajador tiene derecho a quince (15) días hábiles de vacaciones "
    "remuneradas por cada año de servicio."
)
REPETICION = (
    "En el evento de ser condenado el Estado a la reparación patrimonial, deberá "
    "repetir contra el agente que actuó con culpa grave."
)


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "ENVIRONMENT": "test",
        "EMBEDDING_PROVIDER": "mock",
        "RERANKER_PROVIDER": "mock",
        "_env_file": None,
    }
    return Settings(**(base | overrides))  # type: ignore[arg-type]


# --- Mock reranker ----------------------------------------------------------


async def test_mock_ranks_a_relevant_passage_first() -> None:
    provider = MockRerankerProvider()

    results = await provider.rerank(
        "responsabilidad patrimonial del Estado por daño antijurídico",
        [VACACIONES, RESPONSABILIDAD],
    )

    assert results[0].index == 1


async def test_mock_scores_an_unrelated_passage_near_zero() -> None:
    """The evidence threshold must stay meaningful: a passage that answers nothing
    cannot come back looking confident."""
    provider = MockRerankerProvider()

    results = await provider.rerank("término de caducidad tributaria", [VACACIONES])

    assert results[0].score < 0.35


async def test_mock_is_deterministic() -> None:
    provider = MockRerankerProvider()

    first = await provider.rerank("daño antijurídico", [RESPONSABILIDAD, VACACIONES])
    second = await provider.rerank("daño antijurídico", [RESPONSABILIDAD, VACACIONES])

    assert first == second


async def test_mock_ignores_stopword_only_queries() -> None:
    """"de la que en" carries no signal; inventing scores for it would let a
    meaningless query clear the evidence threshold."""
    provider = MockRerankerProvider()

    results = await provider.rerank("de la que en el", [RESPONSABILIDAD, VACACIONES])

    assert all(result.score == 0.0 for result in results)


async def test_mock_is_accent_insensitive() -> None:
    """Colombian sources are inconsistently accented; scoring must not depend on it."""
    provider = MockRerankerProvider()

    with_accents = await provider.rerank("daño antijurídico", [RESPONSABILIDAD])
    without = await provider.rerank("dano antijuridico", [RESPONSABILIDAD])

    assert with_accents[0].score == without[0].score


async def test_mock_respects_top_n() -> None:
    provider = MockRerankerProvider()

    results = await provider.rerank(
        "responsabilidad del Estado", [RESPONSABILIDAD, REPETICION, VACACIONES], top_n=2
    )

    assert len(results) == 2


async def test_mock_returns_indices_into_the_input_list() -> None:
    provider = MockRerankerProvider()

    results = await provider.rerank("vacaciones remuneradas", [RESPONSABILIDAD, VACACIONES])

    assert {result.index for result in results} == {0, 1}


async def test_mock_handles_an_empty_document_list() -> None:
    assert await MockRerankerProvider().rerank("consulta", []) == []


# --- NoOp reranker ----------------------------------------------------------


async def test_noop_preserves_retrieval_order() -> None:
    results = await NoOpReranker().rerank("q", [VACACIONES, RESPONSABILIDAD])

    assert [result.index for result in results] == [0, 1]


async def test_noop_scores_below_the_evidence_threshold() -> None:
    """An instance that lost its reranker must not keep answering as though
    evidence had been confirmed."""
    results = await NoOpReranker().rerank("q", [RESPONSABILIDAD])

    assert results[0].score == 0.0
    assert results[0].score < _settings().MIN_EVIDENCE_SCORE


# --- Alibaba reranker: stubbed transport ------------------------------------


def _provider(handler, **overrides: object) -> AlibabaRerankerProvider:  # type: ignore[no-untyped-def]
    kwargs: dict[str, object] = {
        "api_key": "test-key",
        "model": "gte-rerank-v2",
        "base_url": "https://example.test/api/v1",
        "transport": httpx.MockTransport(handler),
    }
    return AlibabaRerankerProvider(**(kwargs | overrides))  # type: ignore[arg-type]


def _rerank_response(*pairs: tuple[int, float]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "output": {
                "results": [
                    {"index": index, "relevance_score": score} for index, score in pairs
                ]
            },
            "usage": {"total_tokens": 42},
        },
    )


async def test_alibaba_sends_the_native_dashscope_shape() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return _rerank_response((0, 0.9))

    await _provider(handler).rerank("consulta", [RESPONSABILIDAD], top_n=1)

    assert seen["url"] == (
        "https://example.test/api/v1/services/rerank/text-rerank/text-rerank"
    )
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"] == {
        "model": "gte-rerank-v2",
        "input": {"query": "consulta", "documents": [RESPONSABILIDAD]},
        # return_documents false: the response only needs indices and scores, and
        # echoing passages back would put corpus text somewhere it need not be.
        "parameters": {"top_n": 1, "return_documents": False},
    }


async def test_alibaba_maps_scores_by_index_not_by_position() -> None:
    """The provider returns results in relevance order, so the second result may
    refer to input 0. Mapping by position would mis-attribute every score."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _rerank_response((2, 0.95), (0, 0.40))

    results = await _provider(handler).rerank(
        "consulta", [RESPONSABILIDAD, VACACIONES, REPETICION]
    )

    assert results[0].index == 2
    assert results[0].score == pytest.approx(0.95)
    assert results[1].index == 0


async def test_alibaba_sorts_by_descending_score() -> None:
    """The threshold is applied to the first element, so ordering is verified
    rather than assumed from the contract."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _rerank_response((0, 0.10), (1, 0.80))

    results = await _provider(handler).rerank("consulta", [VACACIONES, RESPONSABILIDAD])

    assert [result.index for result in results] == [1, 0]


async def test_alibaba_rejects_an_out_of_range_index() -> None:
    """An index outside the submitted set would attach a score to a passage that
    was never sent — the exact failure this system exists to prevent."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _rerank_response((7, 0.9))

    with pytest.raises(RerankerError, match="index 7"):
        await _provider(handler).rerank("consulta", [RESPONSABILIDAD])


async def test_alibaba_rejects_duplicate_indices() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _rerank_response((0, 0.9), (0, 0.5))

    with pytest.raises(RerankerError, match="duplicate"):
        await _provider(handler).rerank("consulta", [RESPONSABILIDAD, VACACIONES])


async def test_alibaba_rejects_a_malformed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    with pytest.raises(RerankerError, match="output"):
        await _provider(handler).rerank("consulta", [RESPONSABILIDAD])


async def test_alibaba_rejects_a_result_without_a_score() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output": {"results": [{"index": 0}]}})

    with pytest.raises(RerankerError, match="no score"):
        await _provider(handler).rerank("consulta", [RESPONSABILIDAD])


async def test_alibaba_issues_no_request_for_an_empty_document_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call expected")

    assert await _provider(handler).rerank("consulta", []) == []


async def test_alibaba_refuses_more_documents_than_the_service_accepts() -> None:
    """Rejected rather than silently truncated: dropping candidates would change
    what the answer could be grounded in, without saying so."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("no HTTP call expected")

    with pytest.raises(RerankerError, match="limit is"):
        await _provider(handler).rerank("consulta", ["texto"] * (MAX_DOCUMENTS + 1))


async def test_alibaba_reports_a_missing_model_without_retrying() -> None:
    """The failure observed against a workspace with no rerank model deployed:
    HTTP 404 `Model not exist`. Terminal, and named precisely."""
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, json={"code": "InvalidParameter", "message": "Model not exist."})

    with pytest.raises(RerankerError, match="ALIBABA_RERANKER_MODEL"):
        await _provider(handler).rerank("consulta", [RESPONSABILIDAD])

    assert attempts == 1


async def test_alibaba_surfaces_a_credential_error_without_retrying() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(401)

    with pytest.raises(RerankerError, match="credentials"):
        await _provider(handler).rerank("consulta", [RESPONSABILIDAD])

    assert attempts == 1


async def test_alibaba_retries_a_rate_limit_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429)
        return _rerank_response((0, 0.7))

    results = await _provider(handler).rerank("consulta", [RESPONSABILIDAD])

    assert attempts == 2
    assert results[0].score == pytest.approx(0.7)


async def test_alibaba_gives_up_after_the_retry_budget() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with pytest.raises(RerankerError, match="server error"):
        await _provider(handler).rerank("consulta", [RESPONSABILIDAD])


async def test_alibaba_error_never_echoes_the_submitted_passages() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "invalid: CLAUSULA CONFIDENCIAL"})

    with pytest.raises(RerankerError) as exc_info:
        await _provider(handler).rerank("consulta", ["CLAUSULA CONFIDENCIAL"])

    assert "CONFIDENCIAL" not in str(exc_info.value)


def test_alibaba_requires_an_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        AlibabaRerankerProvider(api_key="")


# --- Factory ----------------------------------------------------------------


def test_factory_builds_the_mock_reranker() -> None:
    provider = build_reranker_provider(_settings(RERANKER_PROVIDER="mock"))

    assert isinstance(provider, MockRerankerProvider)


def test_factory_builds_the_noop_reranker_when_disabled() -> None:
    provider = build_reranker_provider(_settings(RERANKER_PROVIDER="none"))

    assert isinstance(provider, NoOpReranker)


def test_factory_builds_alibaba_from_configuration() -> None:
    provider = build_reranker_provider(
        _settings(
            RERANKER_PROVIDER="alibaba",
            ALIBABA_RERANKER_API_KEY=SecretStr("key"),
            ALIBABA_RERANKER_MODEL="gte-rerank-v2",
            ALIBABA_RERANKER_BASE_URL="https://workspace.test/api/v1",
        )
    )

    assert isinstance(provider, AlibabaRerankerProvider)
    assert provider.model_id == "alibaba/gte-rerank-v2"
    assert provider.base_url == "https://workspace.test/api/v1"


def test_factory_fails_fast_when_the_selected_reranker_has_no_key() -> None:
    with pytest.raises(RerankerError, match="ALIBABA_RERANKER_API_KEY"):
        build_reranker_provider(
            _settings(RERANKER_PROVIDER="alibaba", ALIBABA_RERANKER_API_KEY=None)
        )
