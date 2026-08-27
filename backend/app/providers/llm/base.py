"""LLM provider interface.

Kept deliberately narrow. The application never imports the Anthropic SDK
directly, and nothing outside this package knows what a "content block" or a
"stop reason" is. What crosses the boundary is: a system prompt, a message list,
and a completion carrying text plus token counts.

That narrowness is what section 20 of the brief asks for — the model must be
swappable through configuration — and it is also what makes the whole chat
pipeline testable without a network call.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum


class LLMError(Exception):
    """Raised when generation fails."""


class LLMRefusal(LLMError):
    """The model declined to produce output.

    Distinct from a transport failure: nothing is wrong with the system, so the
    caller must surface this to the user rather than retry it.
    """


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(slots=True, frozen=True)
class LLMMessage:
    """One conversational turn.

    The system prompt is NOT a message: it is passed separately, because the
    grounding instructions are the system's, not the conversation's, and must not
    be reachable or overridable by conversation history.
    """

    role: Role
    content: str


@dataclass(slots=True)
class LLMCompletion:
    """A finished generation.

    Token counts come from the provider's own usage reporting, never estimated:
    `usage_logs` is the cost record, and an estimate there would make it fiction.
    """

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    #: Provider's stop reason, verbatim. Recorded so a truncated answer is
    #: distinguishable from a complete one.
    stop_reason: str | None = None
    latency_ms: int = 0
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def was_truncated(self) -> bool:
        """True when generation stopped at the token ceiling.

        A truncated legal answer may end mid-sentence, and mid-citation. Callers
        must not present one as complete.
        """
        return self.stop_reason == "max_tokens"


class LLMProvider(ABC):
    """Base class for LLM providers."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """The active model. Recorded per message and per usage row, since the
        configured model can change between turns of one conversation."""

    @abstractmethod
    async def complete(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> LLMCompletion:
        """Generate a completion.

        Args:
            system: system prompt. Carries the grounding rules and the retrieved
                context; never user-supplied.
            messages: conversation turns, oldest first.
            max_tokens: output ceiling. Defaults to the provider's configuration.
            temperature: defaults to the provider's configuration, which for legal
                answers is 0.

        Raises:
            LLMError: the provider refused the request or is unreachable.
        """

    async def stream(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Stream text deltas.

        Optional. The default raises, so a provider that cannot stream says so
        rather than silently degrading — and per section 26 of the brief, the
        non-streaming path is the one correctness is proven on.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support streaming")
        yield ""  # pragma: no cover - unreachable, satisfies AsyncIterator typing
