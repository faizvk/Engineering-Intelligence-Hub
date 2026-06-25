"""Run deterministic retrieval metrics across the golden set.

Reports mean hit_rate / recall@k / precision@k / MRR. Requires a live pgvector
with the demo corpus ingested. expected_source_ids must match the source_uri
your ingestion assigns (see the loaders); de-dup retrieved ids to the doc level.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from evals.retrieval_metrics import (
    hit_rate,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

GOLDEN = Path(__file__).parent / "datasets" / "golden.jsonl"
K = 5


def _retrieved_ids(question: str, k: int) -> list[str]:
    from backend.rag.pipeline import retrieve  # imported lazily (needs DB + API)

    docs = retrieve(question, top_k=k)
    # De-dup to doc-level ids, preserving order.
    seen, ids = set(), []
    for d in docs:
        sid = d.metadata.get("source_id") or d.metadata.get("source_uri", "")
        if sid and sid not in seen:
            seen.add(sid)
            ids.append(sid)
    return ids


def main() -> dict:
    rows = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = {"hit_rate": [], "recall@5": [], "precision@5": [], "mrr": []}
    for row in rows:
        ids = _retrieved_ids(row["question"], K)
        expected = set(row["expected_source_ids"])
        results["hit_rate"].append(hit_rate(ids, expected))
        results["recall@5"].append(recall_at_k(ids, expected, K))
        results["precision@5"].append(precision_at_k(ids, expected, K))
        results["mrr"].append(reciprocal_rank(ids, expected))
    summary = {m: round(statistics.mean(v), 4) for m, v in results.items()}
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
