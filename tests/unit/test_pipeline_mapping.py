"""The Document -> RetrievedChunk adapter preserves identity, source, and score.
Skipped where langchain isn't installed.
"""

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("pydantic")

from langchain_core.documents import Document  # noqa: E402

from backend.rag.pipeline import docs_to_chunks  # noqa: E402
from core.schemas import DocType  # noqa: E402


def test_maps_metadata_to_chunk():
    doc = Document(
        page_content="rotate creds with make rotate-db-creds",
        metadata={
            "source_id": "handbook/db.md",
            "source_uri": "handbook/db.md",
            "chunk_index": 2,
            "doc_type": "doc",
            "title": "DB rotation",
            "relevance_score": 0.91,
        },
    )
    [chunk] = docs_to_chunks([doc])
    assert chunk.doc_id == "handbook/db.md"
    assert chunk.source_uri == "handbook/db.md"
    assert chunk.doc_type is DocType.DOC
    assert chunk.relevance_score == 0.91
    assert "rotate creds" in chunk.text


def test_doc_id_falls_back_to_uri_and_index():
    doc = Document(
        page_content="x",
        metadata={"source_uri": "repo/auth.py", "chunk_index": 3, "doc_type": "code"},
    )
    [chunk] = docs_to_chunks([doc])
    assert chunk.doc_id == "repo/auth.py#3"
    assert chunk.doc_type is DocType.CODE
