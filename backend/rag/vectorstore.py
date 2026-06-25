"""Dense vector search over the canonical prose_chunks / code_chunks tables.

We query pgvector directly (psycopg) behind a LangChain BaseRetriever rather than
using langchain-postgres' PGVector, so dense and lexical retrieval share ONE
schema and the ACL + metadata filters are applied *inside* the SQL (pre-filter),
keeping the k candidates relevant. The query operator (<=>) matches the HNSW
cosine op-class, so the index is actually used. We over-fetch (k≈50); the
reranker downstream trims to the final 6-8.

Filter dialect ($eq/$in/$gte/$lte) matches the metadata-filter router so the same
filter dict flows through dense, lexical, and hybrid retrieval unchanged.
"""

from __future__ import annotations

from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever

from core.db import raw_connect, vector_literal
from core.schemas import DocType

# First-class columns we filter on directly; everything else goes via metadata jsonb.
_COLUMNS = {"doc_type", "repo", "language", "created_at", "source_uri"}
_TABLES = {"prose_chunks", "code_chunks"}


class PgVectorDenseRetriever(BaseRetriever):
    """Approximate-nearest-neighbour search with ACL + metadata pre-filtering."""

    embeddings: Embeddings
    table: str = "prose_chunks"
    k: int = 50
    ef_search: int = 100  # runtime recall/latency dial
    search_filter: dict[str, Any] = {}
    acl_groups: list[str] = ["all"]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        if self.table not in _TABLES:
            raise ValueError(f"unknown table {self.table!r}")
        qvec = self.embeddings.embed_query(query)
        params: dict[str, Any] = {
            "qv": vector_literal(qvec),
            "acl": list(self.acl_groups),
            "k": self.k,
        }
        where = ["acl && %(acl)s::text[]"]  # ACL is non-negotiable
        _compile_filter(self.search_filter, where, params)
        sql = f"""
            SELECT id, content, doc_type, source_uri, chunk_index, repo, title, metadata,
                   1 - (embedding <=> %(qv)s::vector) AS score
            FROM {self.table}
            WHERE {" AND ".join(where)}
            ORDER BY embedding <=> %(qv)s::vector
            LIMIT %(k)s
        """
        with raw_connect() as conn, conn.cursor() as cur:
            cur.execute(f"SET hnsw.ef_search = {int(self.ef_search)}")
            cur.execute(sql, params)
            rows = cur.fetchall()
        return [_row_to_doc(r) for r in rows]


def dense_retriever(
    embeddings: Embeddings,
    *,
    table: str = "prose_chunks",
    k: int = 50,
    search_filter: dict | None = None,
    acl_groups: list[str] | None = None,
) -> PgVectorDenseRetriever:
    return PgVectorDenseRetriever(
        embeddings=embeddings,
        table=table,
        k=k,
        search_filter=search_filter or {},
        acl_groups=acl_groups or ["all"],
    )


def _compile_filter(flt: dict, where: list[str], params: dict) -> None:
    """Translate the $eq/$in/$gte/$lte filter dialect into SQL predicates."""
    for i, (key, cond) in enumerate(flt.items()):
        col = key if key in _COLUMNS else f"metadata->>'{key}'"
        if not isinstance(cond, dict):
            cond = {"$eq": cond}
        for op, val in cond.items():
            pname = f"f{i}_{op.strip('$')}"
            if op == "$eq":
                where.append(f"{col} = %({pname})s")
            elif op == "$in":
                where.append(f"{col} = ANY(%({pname})s)")
            elif op == "$gte":
                where.append(f"{col} >= %({pname})s")
            elif op == "$lte":
                where.append(f"{col} <= %({pname})s")
            else:
                raise ValueError(f"unsupported filter operator {op!r}")
            params[pname] = val


def _row_to_doc(row: tuple) -> Document:
    _id, content, doc_type, source_uri, chunk_index, repo, title, metadata, score = row
    return Document(
        page_content=content,
        metadata={
            "id": str(_id),
            "source_id": source_uri,  # doc-level id for retrieval metrics
            "source_uri": source_uri,
            "chunk_index": chunk_index,
            "doc_type": doc_type or DocType.DOC.value,
            "repo": repo,
            "title": title,
            "dense_score": float(score),
            **(metadata or {}),
        },
    )
