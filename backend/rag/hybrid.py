"""Hybrid retrieval: fuse dense (semantic) and lexical (BM25-adjacent) recall.

A custom BaseRetriever runs both and fuses with explicit RRF (see fusion.py),
so it composes cleanly under the reranker. This is the LangChain EnsembleRetriever
pattern made explicit: recall in two dimensions, semantic and lexical, before the
cross-encoder takes over for precision.
"""

from __future__ import annotations

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever

from backend.rag.fusion import rrf_fuse
from backend.rag.keyword import keyword_retriever
from backend.rag.vectorstore import dense_retriever


class HybridRetriever(BaseRetriever):
    dense: BaseRetriever
    lexical: BaseRetriever
    weights: tuple[float, float] = (0.6, 0.4)  # dense-leaning; tune on the eval set

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        dense_docs = list(self.dense.invoke(query))
        lexical_docs = list(self.lexical.invoke(query))

        by_key: dict[str, Document] = {}
        for doc in dense_docs + lexical_docs:
            by_key.setdefault(_key(doc), doc)

        fused = rrf_fuse(
            [[_key(d) for d in dense_docs], [_key(d) for d in lexical_docs]],
            weights=list(self.weights),
        )
        return [by_key[k] for k, _ in fused if k in by_key]


def _key(doc: Document) -> str:
    return doc.metadata.get("id") or doc.page_content[:128]


def hybrid_retriever(
    embeddings: Embeddings,
    *,
    table: str = "prose_chunks",
    k: int = 50,
    search_filter: dict | None = None,
    acl_groups: list[str] | None = None,
    weights: tuple[float, float] = (0.6, 0.4),
) -> HybridRetriever:
    return HybridRetriever(
        dense=dense_retriever(
            embeddings, table=table, k=k, search_filter=search_filter, acl_groups=acl_groups
        ),
        lexical=keyword_retriever(
            table=table, k=k, search_filter=search_filter, acl_groups=acl_groups
        ),
        weights=weights,
    )
