"""A/B retrieval configs against the golden set.

Decide on quality-per-dollar, not raw quality. This compares hybrid-only vs
hybrid+rerank on MRR so the reranker's contribution is a number, not a hunch.
Requires a live pgvector with the demo corpus. Log results in EXPERIMENTS.md.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from evals.retrieval_metrics import reciprocal_rank

GOLDEN = Path(__file__).parent / "datasets" / "golden.jsonl"

CONFIGS = {
    "hybrid-only": {"rerank": False},
    "hybrid+rerank": {"rerank": True},
}


def _ids(question: str, *, rerank: bool, k: int = 5) -> list[str]:
    from backend.rag.pipeline import retrieve

    docs = retrieve(question, top_k=k, route=False, rerank=rerank)
    seen, ids = set(), []
    for d in docs:
        sid = d.metadata.get("source_id") or d.metadata.get("source_uri", "")
        if sid and sid not in seen:
            seen.add(sid)
            ids.append(sid)
    return ids


def main() -> dict:
    rows = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines() if line.strip()]
    out: dict[str, float] = {}
    for name, cfg in CONFIGS.items():
        mrr = statistics.mean(
            reciprocal_rank(_ids(r["question"], rerank=cfg["rerank"]), set(r["expected_source_ids"]))
            for r in rows
        )
        out[name] = round(mrr, 4)
        print(f"{name:>16}  MRR={out[name]}")
    if "hybrid-only" in out and "hybrid+rerank" in out:
        print(f"rerank delta MRR: {out['hybrid+rerank'] - out['hybrid-only']:+.4f}")
    return out


if __name__ == "__main__":
    main()
