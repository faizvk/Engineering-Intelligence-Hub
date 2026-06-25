"""Reranking — the highest-ROI quality lever.

The bi-encoder (embeddings) shortlists ~50 candidates by vector similarity; a
cross-encoder reranker reads each (query, chunk) pair jointly and returns the
true top-k. We wrap Voyage rerank-2.5 as a VoyageAIRerank compressor inside a
ContextualCompressionRetriever, so it slots over ANY base retriever (dense now,
hybrid later) without the rest of the pipeline changing.

Each returned Document carries a relevance_score in metadata — surfaced in
traces and usable as a score floor to drop junk on thin-result queries.
"""

from __future__ import annotations

from langchain.retrievers import ContextualCompressionRetriever
from langchain_core.retrievers import BaseRetriever, RetrieverLike
from langchain_voyageai import VoyageAIRerank

from core.settings import get_settings


def reranking_retriever(
    base_retriever: RetrieverLike,
    *,
    top_k: int = 8,
) -> BaseRetriever:
    s = get_settings()
    compressor = VoyageAIRerank(model=s.rerank_model, top_k=top_k)
    return ContextualCompressionRetriever(
        base_compressor=compressor,
        base_retriever=base_retriever,
    )
