"""OpenAI-compatible LLM provider.

Communicates with OpenAI-compatible endpoints (such as Nodule, vLLM, LiteLLM, Ollama, OpenRouter)
supporting Claude, GPT, and Gemini models with precise token usage telemetry.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.logging import get_logger
from app.providers.llm.base import (
    LLMCompletion,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRefusal,
    Role,
)

logger = get_logger(__name__)


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://access.nodule-provider.store/v1",
        model: str = "claude-sonnet-4.6",
        max_tokens: int = 4096,
        temperature: float = 0.0,
        timeout: float = 120.0,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required for OpenAICompatibleProvider")

        self.api_key = api_key
        # Strip trailing slash
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

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

        active_model = model or self.model
        active_max_tokens = max_tokens or self.max_tokens
        active_temp = self.temperature if temperature is None else temperature

        payload_messages: list[dict[str, str]] = []
        if system.strip():
            payload_messages.append({"role": "system", "content": system})

        for msg in messages:
            payload_messages.append({
                "role": "user" if msg.role == Role.USER else "assistant",
                "content": msg.content,
            })

        body: dict[str, Any] = {
            "model": active_model,
            "messages": payload_messages,
            "max_tokens": active_max_tokens,
            "temperature": active_temp,
        }

        t0 = time.perf_counter()
        try:
            resp = await self._client.post("/chat/completions", json=body)
        except httpx.ConnectError as exc:
            raise LLMError(f"Could not reach LLM endpoint at {self.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise LLMError(f"LLM request timed out after {self.timeout}s") from exc
        except Exception as exc:
            raise LLMError(f"LLM request failed: {type(exc).__name__}") from exc

        latency_ms = int((time.perf_counter() - t0) * 1000)

        if resp.status_code != 200:
            err_text = resp.text
            logger.error("LLM provider returned error status", extra={"status": resp.status_code, "body": err_text})
            raise LLMError(f"LLM API error (HTTP {resp.status_code}): {err_text[:200]}")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise LLMRefusal("LLM returned empty choices")

        choice = choices[0]
        msg_obj = choice.get("message", {})
        text_content = msg_obj.get("content") or ""
        finish_reason = choice.get("finish_reason", "stop")

        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return LLMCompletion(
            text=text_content,
            model=data.get("model", active_model),
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            stop_reason=finish_reason,
            latency_ms=latency_ms,
            metadata={
                "provider": "openai_compatible",
                "base_url": self.base_url,
                "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens", 0),
            },
        )

    async def stream(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        if not messages:
            raise LLMError("At least one message is required")

        active_model = model or self.model
        active_max_tokens = max_tokens or self.max_tokens
        active_temp = self.temperature if temperature is None else temperature

        payload_messages: list[dict[str, str]] = []
        if system.strip():
            payload_messages.append({"role": "system", "content": system})

        for msg in messages:
            payload_messages.append({
                "role": "user" if msg.role == Role.USER else "assistant",
                "content": msg.content,
            })

        body: dict[str, Any] = {
            "model": active_model,
            "messages": payload_messages,
            "max_tokens": active_max_tokens,
            "temperature": active_temp,
            "stream": True,
        }

        try:
            req = self._client.build_request("POST", "/chat/completions", json=body)
            resp = await self._client.send(req, stream=True)
        except Exception as exc:
            raise LLMError(f"LLM streaming request failed: {type(exc).__name__}") from exc

        if resp.status_code != 200:
            err_text = await resp.aread()
            await resp.aclose()
            raise LLMError(f"LLM streaming API error (HTTP {resp.status_code}): {err_text.decode()[:200]}")

        try:
            async for line in resp.aiter_lines():
                if not line:
                    continue
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
                except Exception:
                    continue
        finally:
            await resp.aclose()

