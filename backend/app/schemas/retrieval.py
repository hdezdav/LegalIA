"""Retrieval types.

`RetrievalCandidate` is the unit that flows through the whole pipeline: vector
search and lexical search both produce it, fusion merges it, the reranker
reorders it, context construction consumes it, and citations are built from it.
Carrying provenance (which arm found it, at what rank, with what score) all the
way through is what makes retrieval quality measurable after the fact.
"""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import (
    Court,
    DocumentStatus,
    DocumentType,
    Jurisdiction,
    LegalArea,
    RetrievalSource,
)


class RetrievalFilters(BaseModel):
    """Metadata filters applied inside the SQL query, before scoring.

    Filtering in the database rather than after retrieval matters: post-filtering
    a top-k would silently return fewer than k results, and a jurisdiction filter
    that drops 9 of 10 candidates would leave almost nothing to rerank.
    """

    model_config = ConfigDict(extra="forbid")

    legal_area: list[LegalArea] | None = None
    jurisdiction: list[Jurisdiction] | None = None
    court: list[Court] | None = None
    document_type: list[DocumentType] | None = None
    status: list[DocumentStatus] | None = None

    published_after: date | None = None
    published_before: date | None = None

    #: Restrict to specific documents. Used by evaluation and by "ask about this
    #: document" flows.
    document_ids: list[uuid.UUID] | None = None

    def is_empty(self) -> bool:
        return not any(
            value is not None for value in self.model_dump(exclude_none=True).values()
        )


class RetrievalCandidate(BaseModel):
    """One retrieved chunk with its provenance and scores."""

    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    document_id: uuid.UUID

    content: str
    section: str | None = None
    article_number: str | None = None
    hierarchy_path: str | None = None
    chunk_index: int
    token_count: int
    char_start: int | None = None
    char_end: int | None = None

    # --- Document context, joined in so citation building needs no second query
    document_title: str
    document_type: DocumentType
    status: DocumentStatus
    source_name: str
    source_url: str | None = None
    publication_date: date | None = None
    issuing_entity: str | None = None
    court: Court | None = None
    legal_area: LegalArea | None = None

    # --- Scores ------------------------------------------------------------
    #: Cosine similarity in [0, 1]. None when this candidate came only from the
    #: lexical arm.
    semantic_score: float | None = None
    #: PostgreSQL ts_rank_cd, unbounded above. None when semantic-only.
    lexical_score: float | None = None
    #: Fused score from Reciprocal Rank Fusion. Comparable across arms.
    fusion_score: float = 0.0
    #: Reranker relevance in [0, 1]. None when reranking did not run.
    rerank_score: float | None = None

    #: Rank within each arm, 1-based. Kept for RRF and for evaluation.
    semantic_rank: int | None = None
    lexical_rank: int | None = None
    #: Final 1-based position after reranking. Copied onto the citation, so a
    #: stored citation records where its source actually placed.
    rank: int | None = None

    retrieval_source: RetrievalSource

    @property
    def score(self) -> float:
        """The score to order by: reranked when available, fused otherwise."""
        return self.rerank_score if self.rerank_score is not None else self.fusion_score


class RetrievalResult(BaseModel):
    """Outcome of one retrieval pass, with the numbers a refusal is justified by."""

    candidates: list[RetrievalCandidate] = Field(default_factory=list)

    #: Counts per stage, so a thin result can be attributed to the right arm.
    semantic_count: int = 0
    lexical_count: int = 0
    #: Distinct candidates after fusion and deduplication.
    fused_count: int = 0
    reranked: bool = False

    embedding_latency_ms: int = 0
    retrieval_latency_ms: int = 0
    rerank_latency_ms: int = 0

    #: True when the lexical arm was unavailable (missing `legal_es`), so the
    #: result is semantic-only and callers can say so instead of implying full
    #: hybrid coverage.
    lexical_degraded: bool = False

    @property
    def top_score(self) -> float | None:
        return self.candidates[0].score if self.candidates else None

    @property
    def is_empty(self) -> bool:
        return not self.candidates
