"""The score floor drops reranker-judged-weak chunks but keeps unscored ones.
Pure-stdlib, always green.
"""

from types import SimpleNamespace

from backend.rag.scoring import SCORE_FLOOR, above_floor


def _doc(score):
    return SimpleNamespace(metadata={"relevance_score": score})


def test_drops_below_floor_keeps_above():
    docs = [_doc(0.8), _doc(0.1), _doc(SCORE_FLOOR)]
    kept = above_floor(docs)
    scores = [d.metadata["relevance_score"] for d in kept]
    assert 0.1 not in scores
    assert 0.8 in scores and SCORE_FLOOR in scores


def test_unscored_docs_are_kept():
    # A degraded hybrid-only fallback has no relevance_score — keep those.
    docs = [SimpleNamespace(metadata={"dense_score": 0.5})]
    assert len(above_floor(docs)) == 1


def test_all_weak_yields_empty():
    assert above_floor([_doc(0.05), _doc(0.2)]) == []
