"""The metadata-filter dialect compiles to safe, parameterized SQL predicates."""

import pytest

pytest.importorskip("langchain_core")
pytest.importorskip("psycopg")

from backend.rag.vectorstore import _compile_filter  # noqa: E402


def test_first_class_columns_and_operators():
    where: list[str] = []
    params: dict = {}
    _compile_filter(
        {"doc_type": {"$eq": "incident"}, "repo": {"$in": ["a", "b"]},
         "created_at": {"$gte": "2026-01-01"}},
        where,
        params,
    )
    joined = " ".join(where)
    assert "doc_type = %(" in joined
    assert "repo = ANY(%(" in joined
    assert ">= %(" in joined
    assert len(params) == 3


def test_bare_value_is_eq():
    where: list[str] = []
    _compile_filter({"doc_type": "code"}, where, {})
    assert "doc_type = %(" in where[0]


def test_non_column_key_uses_metadata_jsonb():
    where: list[str] = []
    _compile_filter({"severity": {"$eq": "SEV-1"}}, where, {})
    assert "metadata->>'severity'" in where[0]


def test_unknown_operator_rejected():
    with pytest.raises(ValueError):
        _compile_filter({"x": {"$bad": 1}}, [], {})
