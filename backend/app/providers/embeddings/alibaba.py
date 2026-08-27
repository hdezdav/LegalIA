"""Alibaba embedding provider (DashScope, OpenAI-compatible endpoint).

Uses the OpenAI-compatible surface (`POST {base_url}/embeddings`) rather than the
native DashScope shape, because the request/response contract is stable and
identical across providers, which keeps this class a thin transport layer.

The base URL is configuration, not a constant: a dedicated workspace is served
from its own host, so hardcoding the public endpoint would break that deployment.

Reference: Alibaba Cloud Model Studio, "OpenAI-compatible" embeddings API. The
`dimensions` parameter is supported by text-embedding-v3/v4; it is sent only when
it differs from the model default so an older model that rejects the field still
works.
"""

from __future__ import annotations

import asyncio

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger
from app.providers.embeddings.base import EmbeddingError, EmbeddingProvider

logger = get_logger(__name__)

# The API rejects an oversized batch outright rather than truncating it.
MAX_BATCH_SIZE = 10

# Per-input token ceiling for text-embedding-v4. Chunks are sized well below this
# by CHUNK_SIZE, so exceeding it means a splitter bug, not a corpus problem.
MAX_INPUT_TOKENS = 8192


class _Retryable(EmbeddingError):
    """Transient failure: worth retrying."""


class AlibabaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-v4",
        dimension: int = 1024,
        base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        timeout: float = 60.0,
        batch_size: int = MAX_BATCH_SIZE,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Alibaba API key is required")

        self.api_key = api_key
        self.model = model
        self._dimension = dimension
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.batch_size = min(batch_size, MAX_BATCH_SIZE)
        # Test seam: lets the suite exercise the full request/response contract
        # against a stub, since this integration cannot be verified without a
        # key for a workspace that actually serves an embedding model.
        self._transport = transport

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_id(self) -> str:
        # Dimension is part of the identity: text-embedding-v4 at 1024 and at 512
        # are different vector spaces, and cosine distance between them is
        # meaningless.
        return f"alibaba/{self.model}-{self._dimension}"

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise EmbeddingError("Cannot embed empty text")

        # Split into API-sized batches and run them concurrently, but bounded:
        # the provider rate-limits, and an unbounded gather over a 5,000-chunk
        # document would trip that immediately.
        batches = [
            texts[start : start + self.batch_size]
            for start in range(0, len(texts), self.batch_size)
        ]

        semaphore = asyncio.Semaphore(4)

        # The client is passed down rather than stored on self: two concurrent
        # embed_batch calls (a chat query while ingestion runs) would otherwise
        # share and clobber the same attribute.
        async with httpx.AsyncClient(
            timeout=self.timeout, transport=self._transport
        ) as client:

            async def _run(batch: list[str]) -> list[list[float]]:
                async with semaphore:
                    return await self._embed_one_batch(client, batch)

            results = await asyncio.gather(*(_run(batch) for batch in batches))

        return [vector for batch_result in results for vector in batch_result]

    @retry(
        retry=retry_if_exception_type(_Retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _embed_one_batch(
        self, client: httpx.AsyncClient, batch: list[str]
    ) -> list[list[float]]:
        payload: dict[str, object] = {
            "model": self.model,
            "input": batch,
            "encoding_format": "float",
        }
        # Only sent when non-default, so a model without dimension control is not
        # handed a field it will reject.
        if self._dimension:
            payload["dimensions"] = self._dimension

        try:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise _Retryable(f"Embedding request timed out after {self.timeout}s") from exc
        except httpx.HTTPError as exc:
            raise _Retryable(f"Embedding transport error: {type(exc).__name__}") from exc

        self._raise_for_status(response)

        return self._parse(response.json(), expected=len(batch))

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        """Map HTTP status onto retryable and terminal errors.

        The response body is not echoed: it can quote the submitted text, which
        for a private document must not reach logs or an exception message.
        """
        if response.is_success:
            return

        status = response.status_code

        if status == 429:
            raise _Retryable("Embedding provider rate limit exceeded")
        if status >= 500:
            raise _Retryable(f"Embedding provider server error (HTTP {status})")
        if status in (401, 403):
            raise EmbeddingError(
                f"Embedding provider rejected the credentials (HTTP {status})"
            )
        raise EmbeddingError(f"Embedding provider rejected the request (HTTP {status})")

    def _parse(self, body: dict, expected: int) -> list[list[float]]:
        """Extract vectors, validating shape and order.

        The API returns items carrying an `index`; they are sorted by it rather
        than trusted to arrive in order, because a silently reordered batch would
        attach every embedding to the wrong chunk.
        """
        data = body.get("data")
        if not isinstance(data, list) or len(data) != expected:
            raise EmbeddingError(
                f"Embedding provider returned {len(data) if isinstance(data, list) else 0} "
                f"vectors for {expected} inputs"
            )

        try:
            ordered = sorted(data, key=lambda item: item["index"])
        except (KeyError, TypeError) as exc:
            raise EmbeddingError("Embedding response items lack an index") from exc

        vectors: list[list[float]] = []
        for item in ordered:
            vector = item.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise EmbeddingError("Embedding response contained an empty vector")
            if len(vector) != self._dimension:
                raise EmbeddingError(
                    f"Embedding provider returned dimension {len(vector)}, "
                    f"configured dimension is {self._dimension}. Fix "
                    "ALIBABA_EMBEDDING_DIMENSION, or the vectors will not match "
                    "the database column."
                )
            vectors.append([float(component) for component in vector])

        return vectors
