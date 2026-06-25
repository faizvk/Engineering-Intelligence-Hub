"""Orphan computation for idempotent re-index. Pure-stdlib, always green."""

from ingestion.incremental import orphans


def test_shrunk_source_drops_tail_chunks():
    # Source had 5 chunks, now has 3 -> indexes 3,4 are orphans to delete.
    assert orphans({0, 1, 2, 3, 4}, {0, 1, 2}) == {3, 4}


def test_no_orphans_when_unchanged_or_grown():
    assert orphans({0, 1, 2}, {0, 1, 2}) == set()
    assert orphans({0, 1}, {0, 1, 2, 3}) == set()
