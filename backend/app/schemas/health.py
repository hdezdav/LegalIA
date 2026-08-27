"""Health endpoint payloads."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentStatus(StrEnum):
    OK = "ok"
    ERROR = "error"
    # Component is reachable but not fully usable, or intentionally disabled.
    DEGRADED = "degraded"


class HealthResponse(BaseModel):
    """Aggregate health.

    `status` is ok only when every hard dependency is ok. The endpoint returns
    503 in any other case, so an orchestrator never has to parse the body.
    """

    status: ComponentStatus
    database: ComponentStatus
    pgvector: ComponentStatus
    # Lexical retrieval depends on the `legal_es` FTS configuration. Reported
    # separately because losing it degrades retrieval quality without breaking
    # the API.
    text_search: ComponentStatus

    version: str
    environment: str

    # Which providers are active. Makes it obvious from the outside whether an
    # instance is running on mock providers.
    embedding_provider: str
    embedding_dimension: int
    reranker_provider: str
    llm_model: str

    detail: str | None = Field(
        default=None,
        description="Set when status is not ok; names the failing components.",
    )
