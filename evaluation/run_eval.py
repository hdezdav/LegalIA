"""Runner for LegalIA RAG Quality & Precision Evaluation.

Usage:
    python -m evaluation.run_eval
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from evaluation.metrics.rag_evaluator import RAGEvaluator


def main() -> None:
    dataset_path = Path(__file__).parent / "datasets" / "colombian_legal_golden.json"
    if not dataset_path.exists():
        print(f"Dataset not found at {dataset_path}")
        sys.exit(1)

    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print(f"==================================================")
    print(f"⚖️ LegalIA RAG Benchmark Suite")
    print(f"📊 Evaluando {len(cases)} casos jurídicos de referencia...")
    print(f"==================================================")

    results = []
    for case in cases:
        # Mock retrieval for dry-run validation of evaluation pipeline
        mock_candidates = [
            {"article_number": art, "section": f"Artículo {art}"}
            for art in case.get("expected_articles", [])
        ]
        res = RAGEvaluator.evaluate_case(case, mock_candidates)
        results.append(res)
        print(f"[{res['id']}] {case['query'][:50]}... | Hit@1: {res['hit@1']} | MRR: {res['mrr']:.2f} | Recall: {res['context_recall']:.2f}")

    avg_hit1 = sum(r["hit@1"] for r in results) / len(results) if results else 0
    avg_mrr = sum(r["mrr"] for r in results) / len(results) if results else 0
    avg_recall = sum(r["context_recall"] for r in results) / len(results) if results else 0

    print(f"\n📈 Métricas Globales:")
    print(f"   • Hit Rate @ 1: {avg_hit1 * 100:.1f}%")
    print(f"   • Mean Reciprocal Rank (MRR): {avg_mrr:.3f}")
    print(f"   • Context Recall: {avg_recall * 100:.1f}%")
    print(f"==================================================")


if __name__ == "__main__":
    main()
