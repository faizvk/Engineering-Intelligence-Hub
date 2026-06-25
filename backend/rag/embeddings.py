"""VoyageAIEmbeddings adapters for the LangChain query path.

Going through the Embeddings interface (rather than the raw SDK) means the
embedder is swappable and .embed_query() / .embed_documents() pick the right
input_type automatically. The output_dimension MUST match ingestion and the
vector(N) column width.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_voyageai import VoyageAIEmbeddings

from core.settings import get_settings


@lru_cache
def text_embeddings() -> VoyageAIEmbeddings:
    s = get_settings()
    return VoyageAIEmbeddings(model=s.embed_model, output_dimension=s.embed_dim)


@lru_cache
def code_embeddings() -> VoyageAIEmbeddings:
    s = get_settings()
    return VoyageAIEmbeddings(model=s.embed_model_code, output_dimension=s.embed_dim)
