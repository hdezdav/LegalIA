"""Hybrid retrieval: semantic + lexical, fused.

Two arms run over the same corpus and their results are merged with Reciprocal
Rank Fusion:

* **Semantic** — pgvector cosine distance over chunk embeddings. Finds passages
  that answer the question without sharing its words ("¿puedo demandar al Estado
  por un daño?" → "responderá patrimonialmente por los daños antijurídicos").
* **Lexical** — PostgreSQL full-text search over the `legal_es` configuration.
  Finds the passages semantic search is worst at: exact article numbers, case
  numbers, defined terms, proper names.

Neither arm is sufficient alone for legal retrieval. Semantic search will happily
return a *conceptually similar* article when the user asked for article 90
specifically; lexical search cannot find a paraphrase. RRF is used rather than a
weighted score sum because the two scores are not comparable — cosine similarity
is bounded in [0,1], `ts_rank_cd` is unbounded and corpus-dependent — so summing
them would let whichever arm happens to produce larger numbers dominate.

Three invariants this module holds:

1. **Filters are applied in SQL, before limiting.** Post-filtering a top-k would
   silently return fewer results than asked for.
2. **Only vectors from the active embedding model are searched.** Mixing two
   embedding spaces produces meaningless rankings, and the failure is invisible.
3. **A missing `legal_es` configuration degrades to semantic-only and says so**,
   rather than failing the request or pretending full hybrid coverage.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from sqlalchemy import Select, and_, func, or_, select, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.text import normalize_query
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.enums import RetrievalSource
from app.providers.embeddings.base import EmbeddingError, EmbeddingProvider
from app.providers.reranking.base import RerankerError, RerankerProvider
from app.schemas.retrieval import (
    RetrievalCandidate,
    RetrievalFilters,
    RetrievalResult,
)

logger = get_logger(__name__)

#: FTS configuration created in infrastructure/postgres/init.sql. Passed
#: explicitly on every call rather than relying on the database default.
FTS_CONFIG = "public.legal_es"

@dataclass(slots=True)
class _Hit:
    """One arm's result before fusion."""

    chunk_id: uuid.UUID
    rank: int
    score: float
    row: tuple


#: Columns every arm selects, so both produce identically-shaped rows and a
#: candidate can be built without a second query per chunk.
_COLUMNS = (
    Chunk.id,
    Chunk.document_id,
    Chunk.content,
    Chunk.section,
    Chunk.article_number,
    Chunk.hierarchy_path,
    Chunk.chunk_index,
    Chunk.token_count,
    Chunk.char_start,
    Chunk.char_end,
    Document.title,
    Document.document_type,
    Document.status,
    Document.source_name,
    Document.source_url,
    Document.publication_date,
    Document.issuing_entity,
    Document.court,
    Document.legal_area,
)


def _base_query() -> Select:
    """Chunk joined to its document, restricted to searchable rows."""
    return (
        select(*_COLUMNS)
        .join(Document, Chunk.document_id == Document.id)
        # A chunk with no vector was never embedded; it cannot participate in
        # semantic search and would be a dead entry in lexical results.
        .where(Chunk.embedding.is_not(None))
    )


def _apply_filters(
    query: Select, filters: RetrievalFilters | None, model_id: str
) -> Select:
    """Narrow a query by metadata, in SQL, before any limit is applied.

    `model_id` is not optional: it restricts the search to vectors produced by the
    active embedding model. Without it, a corpus embedded with two providers would
    return candidates from both spaces, ranked against each other by a cosine
    distance that means nothing across spaces.
    """
    query = query.where(Chunk.embedding_model == model_id)

    if filters is None:
        return query

    if filters.legal_area:
        query = query.where(Document.legal_area.in_(filters.legal_area))
    if filters.jurisdiction:
        query = query.where(Document.jurisdiction.in_(filters.jurisdiction))
    if filters.court:
        query = query.where(Document.court.in_(filters.court))
    if filters.document_type:
        query = query.where(Document.document_type.in_(filters.document_type))
    if filters.status:
        query = query.where(Document.status.in_(filters.status))
    if filters.document_ids:
        query = query.where(Document.id.in_(filters.document_ids))

    # Date filters keep rows with an unknown publication date: a norm whose date
    # was never recorded should not silently vanish from a "since 2010" search.
    # Deciding what to do with it belongs to the answer, not to the filter.
    if filters.published_after:
        query = query.where(
            or_(
                Document.publication_date >= filters.published_after,
                Document.publication_date.is_(None),
            )
        )
    if filters.published_before:
        query = query.where(
            or_(
                Document.publication_date <= filters.published_before,
                Document.publication_date.is_(None),
            )
        )

    return query


def _semantic_search(
    session: Session,
    embedding: list[float],
    limit: int,
    filters: RetrievalFilters | None,
    model_id: str,
    min_similarity: float,
) -> list[_Hit]:
    """Vector search over chunk embeddings.

    Ordered by cosine distance (`<=>`), which the HNSW index on
    `chunks.embedding` serves directly. Similarity is reported as `1 - distance`
    so it reads as "higher is better" everywhere downstream.
    """
    distance = Chunk.embedding.cosine_distance(embedding)

    query = _apply_filters(_base_query(), filters, model_id)
    query = (
        query.add_columns(distance.label("distance"))
        # Expressed as a distance ceiling rather than a similarity floor so the
        # index ordering is preserved.
        .where(distance <= (1.0 - min_similarity))
        .order_by(distance)
        .limit(limit)
    )

    rows = session.execute(query).all()

    return [
        _Hit(
            chunk_id=row[0],
            rank=position,
            score=max(0.0, 1.0 - float(row[-1])),
            row=tuple(row[:-1]),
        )
        for position, row in enumerate(rows, start=1)
    ]


def _lexical_search(
    session: Session,
    query_text: str,
    limit: int,
    filters: RetrievalFilters | None,
    model_id: str,
) -> list[_Hit]:
    """Full-text search over the `legal_es` configuration.

    Uses `websearch_to_tsquery`, which accepts what users actually type — bare
    words, "quoted phrases", `or` — without raising on punctuation the way
    `to_tsquery` does. Ranking is `ts_rank_cd`, which accounts for term proximity:
    for legal text, "responsabilidad" and "patrimonial" adjacent is a much
    stronger signal than the two words far apart in a long article.
    """
    tsquery = func.websearch_to_tsquery(FTS_CONFIG, query_text)
    rank = func.ts_rank_cd(Chunk.content_tsv, tsquery)

    query = _apply_filters(_base_query(), filters, model_id)
    query = (
        query.add_columns(rank.label("rank"))
        .where(Chunk.content_tsv.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(limit)
    )

    rows = session.execute(query).all()

    return [
        _Hit(
            chunk_id=row[0],
            rank=position,
            score=float(row[-1]),
            row=tuple(row[:-1]),
        )
        for position, row in enumerate(rows, start=1)
    ]


def _fuse(
    semantic: list[_Hit],
    lexical: list[_Hit],
    rrf_k: int,
    semantic_weight: float,
    lexical_weight: float,
) -> list[RetrievalCandidate]:
    """Merge both arms with weighted Reciprocal Rank Fusion.

    Each arm contributes `weight / (k + rank)`. Only ranks are used, never raw
    scores: cosine similarity is bounded in [0,1] while `ts_rank_cd` is unbounded
    and corpus-dependent, so adding them directly would let the lexical arm
    dominate purely because its numbers are larger.

    A chunk found by both arms accumulates both terms, which is exactly the
    desired bias: a passage that is both semantically close and lexically on-point
    outranks one that only satisfies a single arm.

    Deduplication is implicit — the accumulator is keyed by chunk_id.
    """
    scores: dict[uuid.UUID, float] = {}
    rows: dict[uuid.UUID, tuple] = {}
    semantic_scores: dict[uuid.UUID, float] = {}
    lexical_scores: dict[uuid.UUID, float] = {}
    semantic_ranks: dict[uuid.UUID, int] = {}
    lexical_ranks: dict[uuid.UUID, int] = {}

    for hit in semantic:
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + semantic_weight / (
            rrf_k + hit.rank
        )
        rows.setdefault(hit.chunk_id, hit.row)
        semantic_scores[hit.chunk_id] = hit.score
        semantic_ranks[hit.chunk_id] = hit.rank

    for hit in lexical:
        scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + lexical_weight / (
            rrf_k + hit.rank
        )
        rows.setdefault(hit.chunk_id, hit.row)
        lexical_scores[hit.chunk_id] = hit.score
        lexical_ranks[hit.chunk_id] = hit.rank

    candidates = [
        _to_candidate(
            row=rows[chunk_id],
            fusion_score=score,
            semantic_score=semantic_scores.get(chunk_id),
            lexical_score=lexical_scores.get(chunk_id),
            semantic_rank=semantic_ranks.get(chunk_id),
            lexical_rank=lexical_ranks.get(chunk_id),
        )
        for chunk_id, score in scores.items()
    ]

    # Ties broken by chunk_id so ordering is deterministic across runs, which
    # evaluation depends on.
    candidates.sort(key=lambda c: (-c.fusion_score, str(c.chunk_id)))
    return candidates


def _to_candidate(
    row: tuple,
    fusion_score: float,
    semantic_score: float | None,
    lexical_score: float | None,
    semantic_rank: int | None,
    lexical_rank: int | None,
) -> RetrievalCandidate:
    """Build a candidate from a selected row, preserving which arm found it."""
    if semantic_score is not None and lexical_score is not None:
        source = RetrievalSource.HYBRID
    elif lexical_score is not None:
        source = RetrievalSource.LEXICAL
    else:
        source = RetrievalSource.SEMANTIC

    return RetrievalCandidate(
        chunk_id=row[0],
        document_id=row[1],
        content=row[2],
        section=row[3],
        article_number=row[4],
        hierarchy_path=row[5],
        chunk_index=row[6],
        token_count=row[7],
        char_start=row[8],
        char_end=row[9],
        document_title=row[10],
        document_type=row[11],
        status=row[12],
        source_name=row[13],
        source_url=row[14],
        publication_date=row[15],
        issuing_entity=row[16],
        court=row[17],
        legal_area=row[18],
        semantic_score=semantic_score,
        lexical_score=lexical_score,
        fusion_score=fusion_score,
        semantic_rank=semantic_rank,
        lexical_rank=lexical_rank,
        retrieval_source=source,
    )


class RetrievalService:
    """Runs the hybrid retrieval pipeline.

    Constructed with its embedding provider rather than reaching for the global
    one, so evaluation can run the same retrieval code against Alibaba and BGE
    without touching this class.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        reranker_provider: RerankerProvider | None = None,
        retrieval_top_k: int | None = None,
        rerank_top_k: int | None = None,
        min_similarity: float | None = None,
        semantic_weight: float | None = None,
        lexical_weight: float | None = None,
        rrf_k: int | None = None,
    ) -> None:
        self.embeddings = embedding_provider
        # Optional so retrieval can be exercised, and evaluated, with reranking
        # off — measuring the reranker's contribution requires being able to
        # remove it.
        self.reranker = reranker_provider
        self.retrieval_top_k = retrieval_top_k or settings.RETRIEVAL_TOP_K
        self.rerank_top_k = rerank_top_k or settings.RERANK_TOP_K
        self.min_similarity = (
            min_similarity if min_similarity is not None else settings.MIN_SIMILARITY_SCORE
        )
        self.semantic_weight = (
            semantic_weight if semantic_weight is not None else settings.SEMANTIC_WEIGHT
        )
        self.lexical_weight = (
            lexical_weight if lexical_weight is not None else settings.LEXICAL_WEIGHT
        )
        self.rrf_k = rrf_k or settings.RRF_K

    async def retrieve(
        self,
        session: Session,
        query: str,
        filters: RetrievalFilters | None = None,
        top_k: int | None = None,
        rerank_top_k: int | None = None,
    ) -> RetrievalResult:
        """Retrieve candidates for `query`.

        Args:
            top_k: candidates to retrieve per arm before fusion.
            rerank_top_k: candidates to keep after reranking. Defaults to
                RERANK_TOP_K; when no reranker is configured, the fused list is
                returned truncated to `top_k`.

        Returns an empty result rather than raising when nothing matches: "no
        evidence" is a legitimate outcome the pipeline must be able to act on, not
        an error.
        """
        limit = top_k or self.retrieval_top_k
        rerank_limit = rerank_top_k or self.rerank_top_k
        normalized = normalize_query(query)

        if not normalized:
            return RetrievalResult()

        started = time.perf_counter()
        try:
            embedding = await self.embeddings.embed_query(normalized)
        except EmbeddingError:
            # Without a query vector there is no semantic arm. Rather than
            # silently returning lexical-only results that look like a normal
            # answer, this propagates: a degraded embedding provider is an
            # operational failure, and the caller decides how to surface it.
            logger.error("query embedding failed", extra={"provider": self.embeddings.model_id})
            raise
        embedding_latency_ms = int((time.perf_counter() - started) * 1000)

        model_id = self.embeddings.model_id

        started = time.perf_counter()
        semantic = _semantic_search(
            session, embedding, limit, filters, model_id, self.min_similarity
        )

        lexical: list[_Hit] = []
        degraded = False
        try:
            lexical = _lexical_search(session, normalized, limit, filters, model_id)
        except DatabaseError as exc:
            # Almost always a missing `legal_es` configuration, which the health
            # endpoint reports as degraded. Semantic search still answers, so the
            # request continues with the loss recorded rather than failing.
            session.rollback()
            degraded = True
            logger.warning(
                "lexical retrieval unavailable, continuing semantic-only",
                extra={"error_type": type(exc).__name__},
            )

        retrieval_latency_ms = int((time.perf_counter() - started) * 1000)

        fused = _fuse(
            semantic,
            lexical,
            rrf_k=self.rrf_k,
            semantic_weight=self.semantic_weight,
            lexical_weight=self.lexical_weight,
        )
        fused_count = len(fused)

        candidates = fused[:limit]
        reranked = False
        rerank_latency_ms = 0

        if self.reranker is not None and candidates:
            started = time.perf_counter()
            candidates, reranked = await self._rerank(normalized, candidates, rerank_limit)
            rerank_latency_ms = int((time.perf_counter() - started) * 1000)

        logger.info(
            "retrieval complete",
            extra={
                "semantic_count": len(semantic),
                "lexical_count": len(lexical),
                "fused_count": fused_count,
                "returned_count": len(candidates),
                "reranked": reranked,
                "embedding_latency_ms": embedding_latency_ms,
                "retrieval_latency_ms": retrieval_latency_ms,
                "rerank_latency_ms": rerank_latency_ms,
                "lexical_degraded": degraded,
            },
        )

        return RetrievalResult(
            candidates=candidates,
            semantic_count=len(semantic),
            lexical_count=len(lexical),
            fused_count=fused_count,
            reranked=reranked,
            embedding_latency_ms=embedding_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            lexical_degraded=degraded,
        )

    async def _rerank(
        self, query: str, candidates: list[RetrievalCandidate], top_k: int
    ) -> tuple[list[RetrievalCandidate], bool]:
        """Reorder candidates by cross-encoder relevance.

        Returns the candidates and whether reranking actually happened. On provider
        failure the fused order is kept and `reranked` is False, so the caller can
        tell a confirmed ranking from a fallback — that distinction matters because
        the evidence threshold is applied to a reranker score, and a fused score is
        not comparable to it.

        Scores are re-associated by the provider's returned index, never by
        position: trusting order here would attach a score to the wrong passage and
        produce a citation pointing at text the model never saw.
        """
        assert self.reranker is not None

        try:
            results = await self.reranker.rerank(
                query, [candidate.content for candidate in candidates], top_n=top_k
            )
        except RerankerError as exc:
            # Retrieval already produced usable candidates. Failing the whole
            # request here would turn a degraded ranking into no answer at all,
            # so the fused order is kept and the loss is recorded.
            logger.warning(
                "reranking failed, falling back to fused order",
                extra={
                    "error_type": type(exc).__name__,
                    "reranker": self.reranker.model_id,
                },
            )
            return candidates[:top_k], False

        reordered: list[RetrievalCandidate] = []
        for rank, result in enumerate(results, start=1):
            candidate = candidates[result.index]
            reordered.append(
                candidate.model_copy(update={"rerank_score": result.score, "rank": rank})
            )

        return reordered, True

    def count_searchable_chunks(self, session: Session) -> int:
        """Chunks embedded with the active model.

        Distinguishes "the corpus is empty" from "the corpus was embedded with a
        different model", which look identical from a zero-result search.
        """
        return (
            session.scalar(
                select(func.count())
                .select_from(Chunk)
                .where(
                    and_(
                        Chunk.embedding.is_not(None),
                        Chunk.embedding_model == self.embeddings.model_id,
                    )
                )
            )
            or 0
        )


def check_fts_available(session: Session) -> bool:
    """True when `legal_es` exists and `websearch_to_tsquery` accepts it."""
    try:
        session.execute(
            select(func.websearch_to_tsquery(FTS_CONFIG, text("'prueba'")))
        )
        return True
    except DatabaseError:
        session.rollback()
        return False
