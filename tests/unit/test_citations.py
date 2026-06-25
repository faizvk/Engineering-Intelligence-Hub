"""Citation parsing maps document_index back to the originating chunk and never
crashes on a missing/out-of-range index. Skipped where pydantic isn't installed.
"""

from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic")

from backend.llm.blocks import extract_citations  # noqa: E402
from core.schemas import RetrievedChunk  # noqa: E402


def _chunks():
    return [
        RetrievedChunk(doc_id="auth#0", title="Auth", text="...", source_uri="handbook/auth.md"),
        RetrievedChunk(doc_id="db#1", title="DB", text="...", source_uri="handbook/db.md"),
    ]


def test_maps_index_to_chunk():
    block = SimpleNamespace(
        citations=[
            SimpleNamespace(document_index=1, cited_text="rotate creds", document_title="DB"),
        ]
    )
    cits = extract_citations(block, _chunks())
    assert len(cits) == 1
    assert cits[0].source_uri == "handbook/db.md"
    assert cits[0].doc_id == "db#1"
    assert cits[0].quoted_text == "rotate creds"


def test_out_of_range_index_is_safe():
    block = SimpleNamespace(citations=[SimpleNamespace(document_index=99)])
    cits = extract_citations(block, _chunks())
    assert cits[0].source_uri is None


def test_no_citations_yields_empty():
    assert extract_citations(SimpleNamespace(), _chunks()) == []
