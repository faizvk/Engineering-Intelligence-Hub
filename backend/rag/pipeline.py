"""The single retrieval entrypoint the service layer calls.

Starts as dense-only for the vertical slice. Later phases upgrade `retrieve()`
*in place* — reranking, hybrid (dense+BM25) fusion, query transformation, and
intent routing — without changing this signature, so the API never has to know
which retrieval strategy is active.
"""

from __future__ import annotations

from langchain_core.documents import Document

from backend.rag.embeddings import text_embeddings
from backend.rag.hybrid import hybrid_retriever
from backend.rag.rerank import reranking_retriever
from backend.rag.routing import build_filter, choose_strategy
from backend.rag.scoring import above_floor
from backend.rag.transform import (
    decomposition_retriever,
    hyde_retriever,
    multiquery_retriever,
)
from core.schemas import DocType, RetrievedChunk

FETCH_K = 50  # over-fetch; the reranker trims to top_k


def retrieve(
    question: str,
    *,
    top_k: int = 8,
    table: str = "prose_chunks",
    search_filter: dict | None = None,
    acl_groups: list[str] | None = None,
    route: bool = True,
) -> list[Document]:
    """route -> filter -> choose transform -> hybrid -> rerank.

    Set route=False (or pass an explicit search_filter) to skip the Haiku
    intent/strategy classification — useful for evals and exact-identifier paths.
    """
    if route and search_filter is None:
        search_filter = build_filter(question)
        strategy = choose_strategy(question)
    else:
        strategy = "none"

    hybrid = hybrid_retriever(
        text_embeddings(),
        table=table,
        k=FETCH_K,
        search_filter=search_filter or {},
        acl_groups=acl_groups or ["all"],
    )
    base = reranking_retriever(hybrid, top_k=top_k)

    if strategy == "multiquery":
        retriever = multiquery_retriever(base)
    elif strategy == "hyde":
        retriever = hyde_retriever(base)
    elif strategy == "decomposition":
        retriever = decomposition_retriever(base)
    else:  # "none" — straight hybrid + rerank
        retriever = base

    try:
        docs = list(retriever.invoke(question))[:top_k]
    except Exception:
        # Voyage rerank (or a transform LLM) unavailable — degrade to hybrid-only
        # (dense + BM25, no rerank) rather than 500. Honest, still useful.
        docs = list(hybrid.invoke(question))[:top_k]
    # Drop chunks the reranker judged below the floor; an empty result -> no-answer.
    return above_floor(docs)


def docs_to_chunks(docs: list[Document]) -> list[RetrievedChunk]:
    """Adapt retrieved LangChain Documents to the shared RetrievedChunk model."""
    out: list[RetrievedChunk] = []
    for d in docs:
        m = d.metadata
        source_uri = m.get("source_uri", "")
        out.append(
            RetrievedChunk(
                doc_id=m.get("source_id") or f"{source_uri}#{m.get('chunk_index', 0)}",
                title=m.get("title") or source_uri or "source",
                text=d.page_content,
                source_uri=source_uri,
                doc_type=DocType(m.get("doc_type", "doc")),
                relevance_score=m.get("relevance_score") or m.get("dense_score"),
                metadata=m,
            )
        )
    return out
