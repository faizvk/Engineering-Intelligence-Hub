"""Deterministic retrieval metrics. Pure-stdlib, always green — these gate hard in CI."""

from evals.retrieval_metrics import (
    hit_rate,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)

EXPECTED = {"doc-a", "doc-b"}


def test_hit_rate():
    assert hit_rate(["x", "doc-a", "y"], EXPECTED) == 1.0
    assert hit_rate(["x", "y"], EXPECTED) == 0.0


def test_recall_at_k():
    assert recall_at_k(["doc-a", "x", "doc-b"], EXPECTED, 5) == 1.0
    assert recall_at_k(["doc-a", "x"], EXPECTED, 5) == 0.5


def test_precision_at_k():
    assert precision_at_k(["doc-a", "doc-b", "x", "y"], EXPECTED, 4) == 0.5


def test_reciprocal_rank():
    assert reciprocal_rank(["x", "doc-b", "y"], EXPECTED) == 0.5  # first hit at rank 2
    assert reciprocal_rank(["doc-a"], EXPECTED) == 1.0
    assert reciprocal_rank(["x", "y"], EXPECTED) == 0.0


def test_empty_expected_is_safe():
    assert recall_at_k(["x"], set(), 5) == 0.0
