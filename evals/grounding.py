"""Deterministic citation grounding.

Because answers carry inline citations (Claude returns the exact cited span), we
can verify *programmatically* that each cited span actually appears in the
retrieved context — a cheap, deterministic groundedness check that complements
the LLM-judged RAGAS faithfulness score. Pure-Python, no API.
"""

from __future__ import annotations

from typing import Sequence


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def is_grounded(quoted_text: str | None, contexts: Sequence[str]) -> bool:
    if not quoted_text:
        return False
    q = _norm(quoted_text)
    return any(q in _norm(c) for c in contexts)


def grounded_fraction(quoted_texts: Sequence[str | None], contexts: Sequence[str]) -> float:
    """Fraction of non-empty cited spans found verbatim in the context.

    No cited spans -> 1.0 (nothing claimed, nothing to be ungrounded).
    """
    claims = [q for q in quoted_texts if q]
    if not claims:
        return 1.0
    return sum(1 for q in claims if is_grounded(q, contexts)) / len(claims)
