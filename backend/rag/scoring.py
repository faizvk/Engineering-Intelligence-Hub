"""Relevance score floor + the honest no-answer path.

If every reranked candidate scores below the floor, the right move is to say
"I couldn't find this" — cheaper and more trustworthy than feeding junk to Claude
and hoping. Kept dependency-free so it's unit-testable.

Unscored docs (e.g. from a degraded hybrid-only fallback that skipped rerank)
are kept — the floor only filters chunks the reranker actually judged weak.
"""

from __future__ import annotations

SCORE_FLOOR = 0.3
NO_ANSWER = "I couldn't find this in the knowledge base."


def above_floor(docs, floor: float = SCORE_FLOOR):
    kept = []
    for d in docs:
        score = d.metadata.get("relevance_score")
        if score is None or score >= floor:
            kept.append(d)
    return kept
