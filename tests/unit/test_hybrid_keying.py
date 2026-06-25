"""Hybrid fusion keys on chunk id when present, else a content prefix."""

import pytest

pytest.importorskip("langchain_core")

from langchain_core.documents import Document  # noqa: E402

from backend.rag.hybrid import _key  # noqa: E402


def test_key_prefers_id():
    doc = Document(page_content="anything", metadata={"id": "42"})
    assert _key(doc) == "42"


def test_key_falls_back_to_content_prefix():
    doc = Document(page_content="x" * 300, metadata={})
    assert _key(doc) == "x" * 128
