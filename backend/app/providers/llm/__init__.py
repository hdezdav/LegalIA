"""LLM provider selection.

One place decides which provider is active. Supports both native Anthropic SDK
and OpenAI-compatible endpoints (such as Nodule, LiteLLM, vLLM, OpenRouter)
supporting Claude, GPT, and Gemini models.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, settings
from app.core.logging import get_logger
from app.providers.llm.base import (
    LLMCompletion,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRefusal,
    Role,
)
from app.providers.llm.mock import MockBehaviour, MockLLMProvider
from app.providers.llm.openai_compatible import OpenAICompatibleProvider

logger = get_logger(__name__)


def build_llm_provider(config: Settings) -> LLMProvider:
    """Construct the answer-generating provider."""
    # 1. Check OpenAI-compatible provider / Nodule
    llm_key = ""
    if config.LLM_API_KEY:
        llm_key = config.LLM_API_KEY.get_secret_value().strip()
    elif config.ANTHROPIC_API_KEY:
        llm_key = config.ANTHROPIC_API_KEY.get_secret_value().strip()

    if config.LLM_PROVIDER == "openai_compatible" and llm_key:
        return OpenAICompatibleProvider(
            api_key=llm_key,
            base_url=config.LLM_BASE_URL,
            model=config.LLM_MODEL,
            max_tokens=config.ANTHROPIC_MAX_TOKENS,
            temperature=config.ANTHROPIC_TEMPERATURE,
            timeout=config.ANTHROPIC_TIMEOUT_SECONDS,
        )

    # 2. Check native Anthropic provider
    if config.ANTHROPIC_API_KEY:
        api_key = config.ANTHROPIC_API_KEY.get_secret_value().strip()
        if api_key:
            from app.providers.llm.anthropic import AnthropicProvider

            return AnthropicProvider(
                api_key=api_key,
                model=config.ANTHROPIC_MODEL,
                max_tokens=config.ANTHROPIC_MAX_TOKENS,
                temperature=config.ANTHROPIC_TEMPERATURE,
                timeout=config.ANTHROPIC_TIMEOUT_SECONDS,
                max_retries=config.ANTHROPIC_MAX_RETRIES,
            )

    if config.is_production:
        raise LLMError(
            "LLM_API_KEY or ANTHROPIC_API_KEY is required to generate answers. "
            "Set it, or run with ENVIRONMENT=development to use the mock."
        )

    logger.warning(
        "no LLM API key set; using the mock LLM provider. Answers are "
        "quoted directly from retrieved context and are not model-generated"
    )
    return MockLLMProvider()


def build_verifier_provider(config: Settings) -> LLMProvider:
    """Construct the provider used by LLM-backed verification."""
    llm_key = ""
    if config.LLM_API_KEY:
        llm_key = config.LLM_API_KEY.get_secret_value().strip()
    elif config.ANTHROPIC_API_KEY:
        llm_key = config.ANTHROPIC_API_KEY.get_secret_value().strip()

    if config.LLM_PROVIDER == "openai_compatible" and llm_key:
        return OpenAICompatibleProvider(
            api_key=llm_key,
            base_url=config.LLM_BASE_URL,
            model=config.VERIFIER_MODEL,
            max_tokens=1024,
            temperature=0.0,
            timeout=config.ANTHROPIC_TIMEOUT_SECONDS,
        )

    if config.ANTHROPIC_API_KEY:
        api_key = config.ANTHROPIC_API_KEY.get_secret_value().strip()
        if api_key:
            from app.providers.llm.anthropic import AnthropicProvider

            return AnthropicProvider(
                api_key=api_key,
                model=config.VERIFIER_MODEL,
                max_tokens=1024,
                temperature=0.0,
                timeout=config.ANTHROPIC_TIMEOUT_SECONDS,
                max_retries=config.ANTHROPIC_MAX_RETRIES,
            )

    if config.is_production:
        raise LLMError("LLM API key is required for LLM verification")

    return MockLLMProvider(model="mock/verifier")


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """The process-wide answer provider."""
    return build_llm_provider(settings)


@lru_cache(maxsize=1)
def get_verifier_provider() -> LLMProvider:
    """The process-wide verifier provider."""
    return build_verifier_provider(settings)


def reset_llm_providers() -> None:
    """Drop both cached providers. For tests that swap configuration."""
    get_llm_provider.cache_clear()
    get_verifier_provider.cache_clear()


__all__ = [
    "LLMCompletion",
    "LLMError",
    "LLMMessage",
    "LLMProvider",
    "LLMRefusal",
    "MockBehaviour",
    "MockLLMProvider",
    "OpenAICompatibleProvider",
    "Role",
    "build_llm_provider",
    "build_verifier_provider",
    "get_llm_provider",
    "get_verifier_provider",
    "reset_llm_providers",
]
