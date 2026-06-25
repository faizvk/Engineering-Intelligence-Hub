"""The single retrieval entrypoint the service layer calls.

Starts as dense-only for the vertical slice. Later phases upgrade `retrieve()`
*in place* — reranking, hybrid (dense+BM25) fusion, query transformation, and
intent routing — without changing this signature, so the API never has to know
which retrieval strategy is active.
"""

from __future__ import annotations

from langchain_core.documents import Document

from backend.rag.embeddings import text_embeddings
from backend.rag.rerank import reranking_retriever
from backend.rag.vectorstore import dense_retriever
from core.schemas import DocType, RetrievedChunk

FETCH_K = 50  # over-fetch; the reranker trims to top_k


def retrieve(
    question: str,
    *,
    top_k: int = 8,
    table: str = "prose_chunks",
    search_filter: dict | None = None,
    acl_groups: list[str] | None = None,
) -> list[Document]:
    # Recall-then-precision: dense over-fetch (k=50) -> cross-encoder rerank to top_k.
    # Later phases swap the base for the hybrid (dense+BM25) retriever in place.
    base = dense_retriever(
        text_embeddings(),
        table=table,
        k=FETCH_K,
        search_filter=search_filter,
        acl_groups=acl_groups or ["all"],
    )
    retriever = reranking_retriever(base, top_k=top_k)
    return list(retriever.invoke(question))


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
