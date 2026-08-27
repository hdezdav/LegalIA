"""Reranker interface.

Reranking exists because retrieval and relevance are different problems. Hybrid
retrieval optimizes for *recall* — cast a wide net with 20 candidates so the right
passage is somewhere in the set. A cross-encoder reranker then optimizes for
*precision*: it reads the query and each candidate together and scores how well
that passage actually answers this question.

That distinction matters more in legal retrieval than almost anywhere else. A
bi-encoder cannot tell "el término es de treinta (30) días" from "el término es de
diez (10) días" — the two passages are nearly identical in embedding space and
differ only in the number that decides the case. A cross-encoder can.

The reranker is also what makes NO EVIDENCE -> NO ANSWER trustworthy. Fused RRF
scores are relative: the top result of a bad retrieval still scores near the top
of its own list. A reranker score is absolute — "this passage does not answer this
question" is representable — so it is the score the refusal threshold is applied
to.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class RerankerError(Exception):
    """Raised when reranking fails."""


@dataclass(slots=True, frozen=True)
class RerankResult:
    """One reranked document.

    `index` refers back to the caller's input list, so the caller re-associates
    scores with its own candidate objects rather than trusting the provider to
    round-trip them.
    """

    index: int
    score: float


class RerankerProvider(ABC):
    """Base class for reranking providers."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Stable identifier, recorded in usage logs so a change in reranking is
        attributable when retrieval quality moves."""

    @abstractmethod
    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[RerankResult]:
        """Score `documents` against `query`, best first.

        Args:
            query: the user's question, normalized.
            documents: candidate passages, in retrieval order.
            top_n: return at most this many results. None returns all.

        Returns:
            Results sorted by descending score. Scores are comparable across calls
            for the same provider, which is what allows an absolute evidence
            threshold.

        Raises:
            RerankerError: the provider refused the request or is unreachable.
        """


class NoOpReranker(RerankerProvider):
    """Passthrough reranker: preserves retrieval order.

    Used when `RERANKER_PROVIDER=none`. Deliberately explicit rather than a hidden
    fallback — it reports scores of 0.0, which is *below* MIN_EVIDENCE_SCORE, so a
    deployment that quietly lost its reranker cannot keep answering as if evidence
    had been confirmed. Callers must treat a NoOp result as "unranked", not as
    "ranked and confident".
    """

    @property
    def model_id(self) -> str:
        return "none/passthrough"

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[RerankResult]:
        limit = len(documents) if top_n is None else min(top_n, len(documents))
        return [RerankResult(index=i, score=0.0) for i in range(limit)]
