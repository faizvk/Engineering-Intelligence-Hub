"""Deterministic retrieval metrics — pure Python, no LLM. Fast enough to gate on
every commit. Given the top-k source IDs the retriever returns vs the expected set.

MRR is the headline number: it rewards putting the right chunk near the top, which
drives generation quality and lets you keep k (and token cost) small.
"""

from __future__ import annotations

from collections.abc import Sequence


def hit_rate(retrieved: Sequence[str], expected: set[str]) -> float:
    """1.0 if any expected source appears in the retrieved list, else 0.0."""
    return 1.0 if expected & set(retrieved) else 0.0


def recall_at_k(retrieved: Sequence[str], expected: set[str], k: int) -> float:
    top = set(retrieved[:k])
    return len(expected & top) / len(expected) if expected else 0.0


def precision_at_k(retrieved: Sequence[str], expected: set[str], k: int) -> float:
    top = retrieved[:k]
    return sum(1 for r in top if r in expected) / k if top else 0.0


def reciprocal_rank(retrieved: Sequence[str], expected: set[str]) -> float:
    """1/rank of the first relevant hit; 0 if none."""
    for i, doc_id in enumerate(retrieved, start=1):
        if doc_id in expected:
            return 1.0 / i
    return 0.0
