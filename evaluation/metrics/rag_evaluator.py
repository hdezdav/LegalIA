"""RAG Evaluation Metrics for Colombian Legal QA."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class MetricResult:
    """Calculated metric output with breakdown."""
    metric_name: str
    score: float
    details: dict[str, Any]


class RAGEvaluator:
    """Computes retrieval and generation benchmarks for legal retrieval."""

    @staticmethod
    def calculate_hit_rate(
        retrieved_articles: Sequence[str | None],
        expected_articles: Sequence[str],
        k: int = 5,
    ) -> float:
        """Calculate Hit Rate @ K (1.0 if at least one expected article is in top-k)."""
        if not expected_articles:
            return 1.0

        top_k = [a for a in retrieved_articles[:k] if a]
        for exp in expected_articles:
            if any(exp.strip().lower() == str(act).strip().lower() for act in top_k):
                return 1.0
        return 0.0

    @staticmethod
    def calculate_mrr(
        retrieved_articles: Sequence[str | None],
        expected_articles: Sequence[str],
    ) -> float:
        """Calculate Mean Reciprocal Rank (MRR) of first relevant article."""
        if not expected_articles:
            return 1.0

        for rank, act in enumerate(retrieved_articles, start=1):
            if not act:
                continue
            if any(exp.strip().lower() == str(act).strip().lower() for exp in expected_articles):
                return 1.0 / rank
        return 0.0

    @staticmethod
    def calculate_context_recall(
        retrieved_articles: Sequence[str | None],
        expected_articles: Sequence[str],
    ) -> float:
        """Calculate proportion of expected articles retrieved."""
        if not expected_articles:
            return 1.0

        clean_retrieved = {str(a).strip().lower() for a in retrieved_articles if a}
        hits = sum(1 for exp in expected_articles if exp.strip().lower() in clean_retrieved)
        return hits / len(expected_articles)

    @staticmethod
    def calculate_context_precision(
        retrieved_articles: Sequence[str | None],
        expected_articles: Sequence[str],
    ) -> float:
        """Calculate proportion of retrieved articles that are relevant."""
        clean_retrieved = [str(a).strip().lower() for a in retrieved_articles if a]
        if not clean_retrieved:
            return 0.0

        expected_set = {exp.strip().lower() for exp in expected_articles}
        relevant_hits = sum(1 for a in clean_retrieved if a in expected_set)
        return relevant_hits / len(clean_retrieved)

    @classmethod
    def evaluate_case(
        cls,
        case: dict[str, Any],
        retrieved_candidates: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Evaluate a single test case."""
        expected_articles = case.get("expected_articles", [])
        
        # Extract article numbers from candidate section or article_number
        retrieved_articles = []
        for c in retrieved_candidates:
            art = c.get("article_number")
            if not art and c.get("section"):
                match = re.search(r"[Aa]rt[íiÍI]culo\s+([0-9]+[A-Za-z\-]*)", c["section"], re.IGNORECASE)
                if match:
                    art = match.group(1)
            retrieved_articles.append(art)

        hit_at_1 = cls.calculate_hit_rate(retrieved_articles, expected_articles, k=1)
        hit_at_3 = cls.calculate_hit_rate(retrieved_articles, expected_articles, k=3)
        hit_at_5 = cls.calculate_hit_rate(retrieved_articles, expected_articles, k=5)
        mrr = cls.calculate_mrr(retrieved_articles, expected_articles)
        recall = cls.calculate_context_recall(retrieved_articles, expected_articles)
        precision = cls.calculate_context_precision(retrieved_articles, expected_articles)

        return {
            "id": case.get("id"),
            "query": case.get("query"),
            "expected_articles": expected_articles,
            "retrieved_articles": retrieved_articles,
            "hit@1": hit_at_1,
            "hit@3": hit_at_3,
            "hit@5": hit_at_5,
            "mrr": mrr,
            "context_recall": recall,
            "context_precision": precision,
        }
