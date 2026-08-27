"""Deterministic reranker for tests and offline development.

Scores by weighted term overlap between the query and each passage, which gives
the one property retrieval tests need: a passage that shares the query's
distinctive terms outranks one that does not, reproducibly.

Two things it is NOT:

* **A cross-encoder.** It cannot tell "treinta (30) días" from "diez (10) días",
  which is precisely what a real reranker is for. It must never be used to judge
  retrieval quality.
* **Uniformly confident.** Scores land in [0, 1] and a passage with no overlap
  scores near 0, so the NO EVIDENCE -> NO ANSWER threshold is still exercised
  rather than trivially satisfied.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from app.core.text import fold_confusables
from app.providers.reranking.base import RerankerProvider, RerankResult

_TOKEN = re.compile(r"\w+", re.UNICODE)

#: Spanish function words carry no discriminative signal. Without this, every
#: passage scores highly on "de la el en que" and ranking collapses.
_STOPWORDS = frozenset(
    """
    a al algo alguna algunas alguno algunos ante antes aquel aquella aquellas
    aquello aquellos aqui como con contra cual cuales cuando de del desde donde
    dos el ella ellas ello ellos en entre era eran es esa esas ese eso esos esta
    estan estas este esto estos fue fueron ha han hasta hay la las le les lo los
    mas me mi mis mucho muy nada ni no nos nosotros o os otra otras otro otros
    para pero poco por porque que quien quienes se sea sean ser si sin sobre son
    su sus tambien tanto te tiene tienen todo todos tu tus un una unas uno unos
    y ya
    """.split()
)


def _terms(text: str) -> list[str]:
    """Tokenize, fold accents, and drop stopwords.

    Accents are folded here (unlike in embedding or excerpt handling) because this
    is scoring only — the result never becomes stored text.
    """
    folded = (
        fold_confusables(text)
        .lower()
        .translate(str.maketrans("áéíóúüñ", "aeiouun"))
    )
    return [t for t in _TOKEN.findall(folded) if t not in _STOPWORDS and len(t) > 1]


class MockRerankerProvider(RerankerProvider):
    @property
    def model_id(self) -> str:
        return "mock/term-overlap"

    async def rerank(
        self, query: str, documents: list[str], top_n: int | None = None
    ) -> list[RerankResult]:
        if not documents:
            return []

        query_terms = Counter(_terms(query))
        if not query_terms:
            # A query of nothing but stopwords carries no signal. Zero scores keep
            # the evidence threshold meaningful instead of inventing confidence.
            limit = len(documents) if top_n is None else min(top_n, len(documents))
            return [RerankResult(index=i, score=0.0) for i in range(limit)]

        scored = [
            RerankResult(index=i, score=self._score(query_terms, document))
            for i, document in enumerate(documents)
        ]

        # Ties broken by original index so ordering is deterministic, which
        # evaluation depends on.
        scored.sort(key=lambda r: (-r.score, r.index))

        return scored if top_n is None else scored[:top_n]

    @staticmethod
    def _score(query_terms: Counter[str], document: str) -> float:
        """Fraction of query terms present, damped by passage length.

        The length damping matters: without it a long article that happens to
        mention every query term once outranks the short article that is actually
        about the question.
        """
        document_terms = set(_terms(document))
        if not document_terms:
            return 0.0

        matched = sum(count for term, count in query_terms.items() if term in document_terms)
        total = sum(query_terms.values())
        coverage = matched / total

        # Mild penalty for verbosity; log keeps it gentle so a genuinely long
        # relevant article is not buried.
        damping = 1.0 / (1.0 + math.log1p(len(document_terms) / 60.0))

        return round(min(1.0, coverage * damping), 6)
