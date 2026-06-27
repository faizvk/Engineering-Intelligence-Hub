"""End-to-end of the query path with the SDK + retrieval mocked.

Proves the real wiring — service -> docs_to_chunks -> answer() (prompt assembly,
citation document blocks, citation parsing, usage) -> QueryResult — works,
without keys, a DB, or network. Skipped where the stack isn't installed.
"""

from types import SimpleNamespace

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("anthropic")

from langchain_core.documents import Document  # noqa: E402


class _FakeStream:
    """Stands in for client.messages.stream(...)'s context manager."""

    def __init__(self, text, title):
        self._text, self._title = text, title

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield self._text

    def get_final_message(self):
        cit = SimpleNamespace(
            document_index=0,
            cited_text="Postgres is the primary datastore",
            document_title=self._title,
        )
        block = SimpleNamespace(type="text", text=self._text, citations=[cit])
        usage = SimpleNamespace(
            input_tokens=120,
            output_tokens=18,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
        )
        return SimpleNamespace(content=[block], usage=usage, stop_reason="end_turn")


def test_answer_query_end_to_end(monkeypatch):
    import backend.llm.answer as answer_mod
    import backend.rag.service as svc

    answer_text = "Postgres is the primary datastore. [1]"
    doc = Document(
        page_content="The platform's primary datastore is Postgres.",
        metadata={
            "source_uri": "data/handbook/architecture-overview.md",
            "source_id": "data/handbook/architecture-overview.md",
            "chunk_index": 0,
            "doc_type": "doc",
            "title": "Platform Architecture Overview",
            "relevance_score": 0.92,
        },
    )

    # Mock retrieval (no DB) and generation (no Anthropic call).
    monkeypatch.setattr(svc, "retrieve", lambda *a, **k: [doc])
    monkeypatch.setattr(answer_mod, "route", lambda q: "claude-sonnet-4-6")  # skip the router call
    monkeypatch.setattr(
        answer_mod.client.messages,
        "stream",
        lambda **kw: _FakeStream(answer_text, doc.metadata["title"]),
    )

    result = svc.answer_query("What is the primary datastore?")

    assert "Postgres" in result.answer
    assert result.usage is not None and result.usage.input_tokens == 120
    assert len(result.citations) == 1
    assert result.citations[0].source_uri == "data/handbook/architecture-overview.md"
    assert result.contexts and "Postgres" in result.contexts[0]
