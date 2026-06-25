"""RRF must rank a doc hit by BOTH retrievers above a single-list hit, and must
not require the two score scales to align. Pure-stdlib, always green.
"""

from backend.rag.fusion import rrf_fuse


def test_doc_in_both_lists_wins():
    dense = ["A", "B", "C"]
    lexical = ["D", "B", "E"]  # B is the only doc in both
    fused = rrf_fuse([dense, lexical])
    assert fused[0][0] == "B"


def test_rank_position_not_raw_score():
    # Even with wildly different list lengths, fusion is by rank only.
    fused = dict(rrf_fuse([["X"], ["Y", "X", "Z", "W", "V"]]))
    # X is rank 1 in list one and rank 2 in list two -> beats Y (rank 1 only once).
    assert fused["X"] > fused["Y"]


def test_weights_bias_a_retriever():
    dense = ["A", "B"]
    lexical = ["B", "A"]
    heavy_dense = dict(rrf_fuse([dense, lexical], weights=[0.9, 0.1]))
    assert heavy_dense["A"] > heavy_dense["B"]  # dense order wins under heavy weight
