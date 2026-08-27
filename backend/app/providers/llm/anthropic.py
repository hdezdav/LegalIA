"""Anthropic provider.

Talks to the Messages API through the official SDK. Everything provider-specific
is contained here: the rest of the application only ever sees `LLMMessage` and
`LLMCompletion`, so switching model or vendor is a configuration change.

Three decisions worth stating:

* **Token counts come from `response.usage`**, never estimated. `usage_logs` is
  the cost record; an estimate there would make it fiction.
* **`stop_reason` is carried through verbatim.** A `max_tokens` stop means the
  answer may end mid-sentence, possibly mid-citation, and the caller has to be
  able to tell.
* **Retries cover only transient failures.** A 400 or an authentication error is
  terminal — retrying it just burns rate limit and delays the real error.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from app.core.logging import get_logger
from app.providers.llm.base import (
    LLMCompletion,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRefusal,
)

logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        timeout: float = 120.0,
        max_retries: int = 2,
        base_url: str | None = None,
        client: AsyncAnthropic | None = None,
    ) -> None:
        if not api_key and client is None:
            raise ValueError("Anthropic API key is required")

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.base_url = base_url

        # The SDK owns retry and timeout handling: it already distinguishes
        # retryable status codes and honours `retry-after`, which is better than a
        # second layer of backoff wrapped around it.
        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout, "max_retries": max_retries}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = client or AsyncAnthropic(**kwargs)

    @property
    def model_id(self) -> str:
        return self.model

    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMCompletion:
        if not messages:
            raise LLMError("At least one message is required")

        started = time.perf_counter()

        try:
            response = await self._client.messages.create(
                model=model or self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=(
                    temperature if temperature is not None else self.temperature
                ),
                # The grounding rules and retrieved context live here, outside the
                # conversation, so history can never override them.
                system=system,
                messages=[
                    {"role": message.role.value, "content": message.content}
                    for message in messages
                ],
            )
        except anthropic.APIStatusError as exc:
            raise self._map_status_error(exc) from exc
        except anthropic.APIConnectionError as exc:
            # Already retried by the SDK; reaching here means it kept failing.
            raise LLMError(f"Could not reach Anthropic: {type(exc).__name__}") from exc
        except anthropic.AnthropicError as exc:
            raise LLMError(f"Anthropic request failed: {type(exc).__name__}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        text = _extract_text(response)

        if response.stop_reason == "refusal":
            # Nothing is wrong with the system, so this must not be retried; it is
            # surfaced to the user as a refusal.
            raise LLMRefusal("The model declined to answer this request")

        completion = LLMCompletion(
            text=text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
            latency_ms=latency_ms,
        )

        if completion.was_truncated:
            # Logged as a warning because a truncated legal answer can end
            # mid-citation, which downstream verification will then flag.
            logger.warning(
                "generation hit the output ceiling",
                extra={
                    "model": response.model,
                    "output_tokens": response.usage.output_tokens,
                    "latency_ms": latency_ms,
                },
            )

        logger.info(
            "generation complete",
            extra={
                "model": response.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "stop_reason": response.stop_reason,
                "latency_ms": latency_ms,
            },
        )

        return completion

    async def stream(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Stream text deltas as they arrive.

        Note the ordering consequence, which is why section 26 of the brief puts
        streaming second: citation verification can only run on a complete answer,
        so a streamed response reaches the user *before* it has been verified. The
        chat service decides whether that trade is acceptable for a given surface;
        this method only provides the capability.
        """
        if not messages:
            raise LLMError("At least one message is required")

        try:
            async with self._client.messages.stream(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=(
                    temperature if temperature is not None else self.temperature
                ),
                system=system,
                messages=[
                    {"role": message.role.value, "content": message.content}
                    for message in messages
                ],
            ) as stream:
                async for delta in stream.text_stream:
                    yield delta
        except anthropic.APIStatusError as exc:
            raise self._map_status_error(exc) from exc
        except anthropic.AnthropicError as exc:
            raise LLMError(f"Anthropic stream failed: {type(exc).__name__}") from exc

    @staticmethod
    def _map_status_error(exc: anthropic.APIStatusError) -> LLMError:
        """Map an API status error onto an actionable message.

        The response body is never echoed: it can quote the submitted prompt, which
        carries retrieved corpus text and the user's question.
        """
        status = exc.status_code

        if status in (401, 403):
            return LLMError(
                f"Anthropic rejected the credentials (HTTP {status}). "
                "Check ANTHROPIC_API_KEY."
            )
        if status == 404:
            return LLMError(
                f"Anthropic does not recognize the model (HTTP {status}). "
                "Check ANTHROPIC_MODEL."
            )
        if status == 429:
            return LLMError("Anthropic rate limit exceeded")
        if status == 413:
            return LLMError(
                "Request too large for Anthropic. Reduce MAX_CONTEXT_TOKENS or "
                "RERANK_TOP_K."
            )
        if status >= 500:
            return LLMError(f"Anthropic server error (HTTP {status})")

        return LLMError(f"Anthropic rejected the request (HTTP {status})")


def _extract_text(response: anthropic.types.Message) -> str:
    """Concatenate the text blocks of a response.

    A response is a list of content blocks; only text blocks are relevant here.
    Non-text blocks are skipped rather than stringified, so nothing that is not
    model prose can end up in a stored answer.
    """
    parts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ]

    text = "".join(parts).strip()

    if not text:
        raise LLMError("Anthropic returned no text content")

    return text
