"""Alibaba reranker provider (DashScope native rerank service).

Unlike embeddings, reranking has no OpenAI-compatible equivalent, so this speaks
the native DashScope shape:

    POST {base_url}/services/rerank/text-rerank/text-rerank
    {"model": ..., "input": {"query": ..., "documents": [...]},
     "parameters": {"top_n": ..., "return_documents": false}}

`return_documents` is false on purpose: the response only needs indices and
scores, and echoing passages back would double the payload and put corpus text
into an extra place it does not need to be.

VERIFIED 2026-08-26 against workspace ws-2trsorjqmzwfn5ss: that workspace serves
92 models, all generative, and `gte-rerank-v2` returns HTTP 404 "Model not exist"
on both the native and compatible routes. The provider is therefore implemented to
the documented contract and tested against a stubbed transport, per section 43 of
the brief: no invented behaviour, and a mock for tests.
"""

from __future__ import annotations

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.providers.reranking.base import RerankerError, RerankerProvider, RerankResult

logger = get_logger(__name__)

#: Documented ceiling for the rerank service. A larger request is rejected
#: outright, so the caller's candidate set is capped rather than silently cut.
MAX_DOCUMENTS = 500

_RERANK_PATH = "/services/rerank/text-rerank/text-rerank"


class _Retryable(RerankerError):
    """Transient failure: worth retrying."""


class AlibabaRerankerProvider(RerankerProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "gte-rerank-v2",
        base_url: str = "https://dashscope-intl.aliyuncs.com/api/v1",
        timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Alibaba reranker API key is required")

        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Test seam: the full request/response contract is exercised against a
        # stub, since no credential for a rerank-capable workspace is available.
        self._transport = transport

    @property
    def model_id(self) -> str:
        return f"alibaba/{self.model}"

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[RerankResult]:
        if not documents:
            return []

        if len(documents) > MAX_DOCUMENTS:
            raise RerankerError(
                f"Cannot rerank {len(documents)} documents; the limit is "
                f"{MAX_DOCUMENTS}. Reduce RETRIEVAL_TOP_K."
            )

        limit = len(documents) if top_n is None else min(top_n, len(documents))

        async with httpx.AsyncClient(
            timeout=self.timeout, transport=self._transport
        ) as client:
            body = await self._call(client, query, documents, limit)

        return self._parse(body, candidate_count=len(documents))

    @retry(
        retry=retry_if_exception_type(_Retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _call(
        self,
        client: httpx.AsyncClient,
        query: str,
        documents: list[str],
        top_n: int,
    ) -> dict:
        payload = {
            "model": self.model,
            "input": {"query": query, "documents": documents},
            "parameters": {"top_n": top_n, "return_documents": False},
        }

        try:
            response = await client.post(
                f"{self.base_url}{_RERANK_PATH}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise _Retryable(f"Rerank request timed out after {self.timeout}s") from exc
        except httpx.HTTPError as exc:
            raise _Retryable(f"Rerank transport error: {type(exc).__name__}") from exc

        self._raise_for_status(response)

        return response.json()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Map HTTP status onto retryable and terminal errors.

        The response body is never echoed: it can quote the submitted passages,
        which for a private document must not reach logs or an exception message.
        """
        if response.is_success:
            return

        status = response.status_code

        if status == 429:
            raise _Retryable("Reranker rate limit exceeded")
        if status >= 500:
            raise _Retryable(f"Reranker server error (HTTP {status})")
        if status in (401, 403):
            raise RerankerError(f"Reranker rejected the credentials (HTTP {status})")
        if status == 404:
            # The failure mode observed on a workspace with no rerank model
            # deployed. Terminal, and worth naming precisely: retrying or falling
            # back silently would hide a misconfiguration.
            raise RerankerError(
                f"Reranker model not available at this endpoint (HTTP {status}). "
                "Check ALIBABA_RERANKER_MODEL and ALIBABA_RERANKER_BASE_URL."
            )
        raise RerankerError(f"Reranker rejected the request (HTTP {status})")

    def _parse(self, body: dict, candidate_count: int) -> list[RerankResult]:
        """Extract (index, score) pairs, validating every index.

        An out-of-range index would attach a score to the wrong passage and, from
        there, produce a citation pointing at text the model never saw. That is
        exactly the failure this system exists to prevent, so it is rejected rather
        than clamped.
        """
        output = body.get("output")
        if not isinstance(output, dict):
            raise RerankerError("Rerank response is missing its output object")

        results = output.get("results")
        if not isinstance(results, list):
            raise RerankerError("Rerank response is missing its results list")

        parsed: list[RerankResult] = []
        for item in results:
            if not isinstance(item, dict):
                raise RerankerError("Rerank result entry is not an object")

            index = item.get("index")
            score = item.get("relevance_score")

            if not isinstance(index, int) or not 0 <= index < candidate_count:
                raise RerankerError(
                    f"Rerank returned index {index!r} for a set of "
                    f"{candidate_count} documents"
                )
            if not isinstance(score, int | float):
                raise RerankerError(f"Rerank result for index {index} has no score")

            parsed.append(RerankResult(index=index, score=float(score)))

        if len({result.index for result in parsed}) != len(parsed):
            raise RerankerError("Rerank returned duplicate indices")

        # Sorted here rather than trusted: the contract says descending, but the
        # evidence threshold is applied to the first element, so ordering is not
        # something to assume.
        parsed.sort(key=lambda result: (-result.score, result.index))
        return parsed
