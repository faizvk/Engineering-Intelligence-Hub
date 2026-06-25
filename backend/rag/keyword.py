"""Lexical retrieval via Postgres full-text search (tsvector + ts_rank_cd).

Embeddings are lexically blind — a developer searching ConnectionPoolTimeout or
PROD-4821 wants the chunk with that exact token. Native FTS keeps lexical search
in the same Postgres as the vectors (one datastore, always consistent).
websearch_to_tsquery accepts raw user input so queries don't throw. ACL +
metadata filters are applied in-SQL, identically to the dense path.
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from backend.rag.vectorstore import _compile_filter
from core.db import raw_connect
from core.schemas import DocType

_TABLES = {"prose_chunks", "code_chunks"}


class PostgresFTSRetriever(BaseRetriever):
    table: str = "prose_chunks"
    k: int = 50
    search_filter: dict[str, Any] = {}
    acl_groups: list[str] = ["all"]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        if self.table not in _TABLES:
            raise ValueError(f"unknown table {self.table!r}")
        params: dict[str, Any] = {"q": query, "acl": list(self.acl_groups), "k": self.k}
        where = [
            "content_tsv @@ websearch_to_tsquery('english', %(q)s)",
            "acl && %(acl)s::text[]",
        ]
        _compile_filter(self.search_filter, where, params)
        sql = f"""
            SELECT id, content, doc_type, source_uri, chunk_index, repo, title, metadata,
                   ts_rank_cd(content_tsv, websearch_to_tsquery('english', %(q)s)) AS score
            FROM {self.table}
            WHERE {" AND ".join(where)}
            ORDER BY score DESC
            LIMIT %(k)s
        """
        with raw_connect() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [_row_to_doc(r) for r in rows]


def keyword_retriever(
    *,
    table: str = "prose_chunks",
    k: int = 50,
    search_filter: dict | None = None,
    acl_groups: list[str] | None = None,
) -> PostgresFTSRetriever:
    return PostgresFTSRetriever(
        table=table, k=k, search_filter=search_filter or {}, acl_groups=acl_groups or ["all"]
    )


def _row_to_doc(row: tuple) -> Document:
    _id, content, doc_type, source_uri, chunk_index, repo, title, metadata, score = row
    return Document(
        page_content=content,
        metadata={
            "id": str(_id),
            "source_id": source_uri,
            "source_uri": source_uri,
            "chunk_index": chunk_index,
            "doc_type": doc_type or DocType.DOC.value,
            "repo": repo,
            "title": title,
            "lexical_score": float(score),
            **(metadata or {}),
        },
    )
