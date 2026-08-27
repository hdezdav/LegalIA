"""Chat API schemas: OpenAI-compatible.

LibreChat's custom endpoints speak the OpenAI Chat Completions protocol, so that
is the shape LegalIA exposes. This is a transport decision, not an architectural
one: the wire format is OpenAI's, everything behind it (retrieval, grounding,
citations, verification) is LegalIA's, and the brief's rule that the legal logic
must not live in the frontend is untouched.

Speaking a standard protocol also means any OpenAI-compatible client works, which
is exactly the substitutability section 3 asks for.
"""

from __future__ import annotations

import time
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import CitationVerificationStatus, DocumentStatus, VerificationStatus


class ChatCompletionMessage(BaseModel):
    """One turn, in OpenAI's shape."""

    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """An OpenAI-style chat completion request.

    `extra="allow"`: OpenAI clients send many sampling parameters (`top_p`,
    `presence_penalty`, `stream_options`, ...). Rejecting unknown fields would
    make the endpoint fragile against a client we do not control, so they are
    accepted and ignored. The ones LegalIA honours are declared below.
    """

    model_config = ConfigDict(extra="allow")

    model: str = Field(default="legalia", description="Ignored; the active model comes from configuration.")
    messages: list[ChatCompletionMessage] = Field(min_length=1)

    # Honoured.
    stream: bool = False
    max_tokens: int | None = Field(default=None, ge=1, le=8192)

    # Accepted for compatibility, deliberately ignored: a legal answer is
    # generated at temperature 0 so the same question and corpus give the same
    # answer. Letting a client raise it would make answers unreproducible.
    temperature: float | None = None

    # OpenAI's per-end-user identifier. Used to attribute the turn when the
    # caller is a trusted frontend holding a service token.
    user: str | None = None

    def last_user_message(self) -> str:
        """The question to answer.

        Read from the end backwards: LibreChat resends the whole visible
        conversation, and the turn to answer is the final user message.
        """
        for message in reversed(self.messages):
            if message.role == "user":
                return message.content
        raise ValueError("Request contains no user message")

    def history(self) -> list[ChatCompletionMessage]:
        """Prior turns, excluding the final user message and any system prompt.

        A client-supplied system prompt is dropped on purpose: the grounding rules
        are LegalIA's, and a frontend must not be able to replace or weaken them.
        """
        messages = [m for m in self.messages if m.role != "system"]
        return messages[:-1] if messages else []


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatCompletionMessage
    finish_reason: str = "stop"


class CitationSchema(BaseModel):
    """One citation linking answer text to its source."""

    id: str
    position: int
    document_id: str
    chunk_id: str

    # Display fields frozen at answer time
    document_title: str
    section: str | None = None
    source_name: str
    source_url: str | None = None
    publication_date: str | None = None  # ISO date string
    status: DocumentStatus

    # The quoted passage from the chunk
    excerpt: str
    excerpt_char_start: int | None = None
    excerpt_char_end: int | None = None

    # Retrieval provenance
    relevance_score: float | None = None
    rank: int | None = None

    # Verification
    verification_status: CitationVerificationStatus


class LegalIAMetadata(BaseModel):
    """LegalIA's own audit fields, carried alongside the OpenAI payload.

    A non-standard extension: an OpenAI client ignores it, and a LegalIA-aware
    client can render provenance from it. This is where "the answer is
    traceable" becomes machine-readable rather than prose.
    """

    conversation_id: str
    message_id: str

    #: True when the model was never asked, because retrieval did not clear the
    #: evidence threshold. The NO EVIDENCE -> NO ANSWER outcome.
    refused_for_lack_of_evidence: bool
    verification_status: VerificationStatus | None = None

    retrieval_candidate_count: int
    context_chunk_count: int
    top_evidence_score: float | None = None
    reranked: bool
    #: True when lexical retrieval was unavailable, so coverage was semantic-only.
    lexical_degraded: bool = False

    embedding_provider: str
    reranker_provider: str

    latency_ms: int

    #: Citations extracted from the answer, linking to source chunks
    citations: list[CitationSchema] = Field(default_factory=list)


class ChatCompletionResponse(BaseModel):
    """An OpenAI-style chat completion response."""

    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage

    legalia: LegalIAMetadata


class ModelCard(BaseModel):
    """One entry in `GET /models`.

    LibreChat and the frontend use this model card to render model selections,
    token limits, context capacities and provider groupings.
    """

    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "legalia"
    name: str | None = None
    provider: str | None = None
    context_limit: int = 200000
    context_limit_label: str = "200k tokens"
    description: str | None = None
    badge: str | None = None


class ModelList(BaseModel):
    """OpenAI-compatible list of models."""

    object: Literal["list"] = "list"
    data: list[ModelCard]
