"""Reciprocal Rank Fusion.

Fuses several ranked lists by summing weight / (c + rank). Because it scores on
rank *position*, it doesn't require dense cosine scores and BM25 scores to share
a scale — a common failure mode in hand-rolled fusion. A document ranked highly
by either retriever floats up; one ranked highly by both dominates.

This is the algorithm LangChain's EnsembleRetriever implements internally; we use
it explicitly so fusion is transparent and unit-testable.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Hashable, Sequence


def rrf_fuse(
    ranked_lists: Sequence[Sequence[Hashable]],
    weights: Sequence[float] | None = None,
    c: int = 60,
) -> list[tuple[Hashable, float]]:
    """Return (key, fused_score) pairs sorted by score descending."""
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    scores: dict[Hashable, float] = defaultdict(float)
    for lst, w in zip(ranked_lists, weights):
        for rank, key in enumerate(lst, start=1):
            scores[key] += w / (c + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
