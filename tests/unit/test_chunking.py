"""Chunking splits prose into overlapping windows, leaves atomic docs alone, and
numbers chunks deterministically. Skipped where langchain isn't installed.
"""

import pytest

pytest.importorskip("langchain_text_splitters")
pytest.importorskip("langchain_core")

from langchain_core.documents import Document  # noqa: E402

from ingestion.chunking import split_documents  # noqa: E402
from ingestion.schema import DocType  # noqa: E402


def _doc(text, **meta):
    base = {"path": "handbook/x.md", "doc_type": DocType.DOC.value}
    base.update(meta)
    return Document(page_content=text, metadata=base)


def test_long_prose_splits_into_multiple_chunks():
    long_text = ("This is a sentence about the auth service. " * 200).strip()
    chunks = split_documents([_doc(long_text)])
    assert len(chunks) > 1
    # start_index is recorded for precise citations.
    assert all("start_index" in c.metadata for c in chunks)


def test_chunk_index_is_sequential_per_source():
    long_text = ("alpha beta gamma delta epsilon. " * 200).strip()
    chunks = split_documents([_doc(long_text)])
    idxs = [c.metadata["chunk_index"] for c in chunks]
    assert idxs == list(range(len(chunks)))


def test_incidents_are_not_resplit():
    big = "INCIDENT-1\n" + ("x" * 5000)
    chunks = split_documents([_doc(big, doc_type=DocType.INCIDENT.value, path="incidents/1.md")])
    assert len(chunks) == 1
