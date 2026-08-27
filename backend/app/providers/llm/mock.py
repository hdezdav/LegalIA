"""Deterministic LLM provider for tests and offline development.

Section 37 of the brief requires the chat pipeline to be testable without an
external API, and section 23 requires a mock so verification does not depend on a
second live call. This is that provider.

It does not paraphrase or reason. It reads the retrieved context out of the system
prompt and answers by quoting from it, with `[n]` markers. That is enough to
exercise the parts of the pipeline that actually matter here:

* citations resolve to chunks that were really in context;
* excerpts match their source text character for character, so
  `CitationService` verification passes on a well-behaved answer;
* the NO EVIDENCE -> NO ANSWER path is reachable, because an empty context
  produces an explicit refusal rather than invented law.

Failure modes are producible on demand (`behaviour=`), so the tests that matter
most — a model citing a chunk it never saw, or misquoting one — can be written
against a provider that reliably misbehaves.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from enum import StrEnum

from app.providers.llm.base import (
    LLMCompletion,
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRefusal,
)

#: Matches the context blocks the prompt builder emits, e.g.
#: `[1] Artículo 90 — Constitución Política\n<text>`.
_SOURCE_BLOCK = re.compile(
    r"^\[(?P<n>\d+)\][^\n]*\n(?P<body>.*?)(?=^\[\d+\]|\Z)",
    re.MULTILINE | re.DOTALL,
)

REFUSAL_TEXT = (
    "No encontré evidencia suficiente en el corpus disponible para responder "
    "esta consulta."
)


class MockBehaviour(StrEnum):
    """How the mock should behave. Each value targets one pipeline property."""

    #: Quote the provided context and cite it correctly.
    GROUNDED = "grounded"
    #: Refuse for lack of evidence, regardless of context.
    REFUSE = "refuse"
    #: Cite a source number that was never in context. Must be caught as
    #: NOT_IN_CONTEXT.
    FABRICATE_CITATION = "fabricate_citation"
    #: Cite a real source but misquote it. Must be caught as EXCERPT_MISMATCH.
    MISQUOTE = "misquote"
    #: Answer with no citations at all. Must be caught as UNSUPPORTED.
    UNCITED = "uncited"
    #: Stop at the token ceiling, as a truncated generation would.
    TRUNCATED = "truncated"
    #: Raise LLMRefusal, as the real provider does on a refusal stop reason.
    RAISE_REFUSAL = "raise_refusal"
    #: Raise LLMError, as an unreachable provider would.
    RAISE_ERROR = "raise_error"


class MockLLMProvider(LLMProvider):
    def __init__(
        self,
        behaviour: MockBehaviour = MockBehaviour.GROUNDED,
        model: str = "mock/deterministic",
        #: Characters quoted per source. Kept short so an excerpt is a strict
        #: substring of its chunk, which is what verification checks.
        excerpt_chars: int = 160,
    ) -> None:
        self.behaviour = behaviour
        self._model = model
        self.excerpt_chars = excerpt_chars
        #: Every (system, messages) pair seen, so tests can assert on what the
        #: prompt builder actually sent.
        self.calls: list[tuple[str, list[LLMMessage]]] = []

    @property
    def model_id(self) -> str:
        return self._model

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

        self.calls.append((system, list(messages)))

        if self.behaviour is MockBehaviour.RAISE_ERROR:
            raise LLMError("Mock provider was configured to fail")
        if self.behaviour is MockBehaviour.RAISE_REFUSAL:
            raise LLMRefusal("Mock provider was configured to refuse")

        sources = _parse_sources(system)
        text = self._compose(sources)

        return LLMCompletion(
            text=text,
            model=self._model,
            # Deterministic and derived from real lengths, so usage accounting is
            # exercised without pretending to be a true token count.
            input_tokens=max(1, len(system) // 4 + sum(len(m.content) for m in messages) // 4),
            output_tokens=max(1, len(text) // 4),
            stop_reason=(
                "max_tokens" if self.behaviour is MockBehaviour.TRUNCATED else "end_turn"
            ),
            latency_ms=0,
        )

    async def stream(
        self,
        system: str,
        messages: list[LLMMessage],
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[str]:
        """Yield the same text a `complete` call would, word by word."""
        completion = await self.complete(system, messages, max_tokens, temperature)
        for word in completion.text.split(" "):
            yield word + " "

    def _compose(self, sources: dict[int, str]) -> str:
        """Build an answer from the parsed context blocks."""
        if self.behaviour is MockBehaviour.REFUSE or not sources:
            # An empty context must never produce invented law: this is the
            # NO EVIDENCE -> NO ANSWER path.
            return REFUSAL_TEXT

        if self.behaviour is MockBehaviour.FABRICATE_CITATION:
            # A number beyond the context window, which is what a hallucinated
            # citation looks like from the verifier's side.
            return f"Según la norma aplicable, procede la acción [{max(sources) + 5}]."

        if self.behaviour is MockBehaviour.UNCITED:
            return (
                "La jurisprudencia ha establecido de manera reiterada que "
                "procede la reparación, sin que sea necesario acreditar la culpa."
            )

        if self.behaviour is MockBehaviour.MISQUOTE:
            number = min(sources)
            return (
                f'De acuerdo con la fuente, "el término aplicable es de '
                f'noventa (90) días contados a partir de la notificación" [{number}].'
            )

        return self._quote(sources)

    def _quote(self, sources: dict[int, str]) -> str:
        """Quote each source verbatim, with its marker.

        Excerpts are exact substrings, so a well-behaved answer verifies as
        SUPPORTED and a genuine mismatch elsewhere is a real signal.
        """
        sentences = []
        for number in sorted(sources):
            excerpt = _leading_excerpt(sources[number], self.excerpt_chars)
            if excerpt:
                sentences.append(f'"{excerpt}" [{number}]')

        if not sentences:
            return REFUSAL_TEXT

        body = " ".join(sentences)
        if self.behaviour is MockBehaviour.TRUNCATED:
            # Cut mid-sentence, as a real truncation would.
            return f"Con fundamento en las fuentes citadas: {body[: len(body) // 2]}"

        return f"Con fundamento en las fuentes citadas: {body}"


def _parse_sources(system: str) -> dict[int, str]:
    """Extract `[n] -> text` from the prompt's context section."""
    return {
        int(match.group("n")): match.group("body").strip()
        for match in _SOURCE_BLOCK.finditer(system)
    }


def _leading_excerpt(body: str, limit: int) -> str:
    """A verbatim prefix of `body`, ending on a word boundary.

    Collapsing whitespace would break exact-substring verification, so the text is
    sliced rather than reflowed.
    """
    text = body.strip()
    if len(text) <= limit:
        return text

    cut = text[:limit]
    boundary = cut.rfind(" ")
    return cut[:boundary] if boundary > 0 else cut
