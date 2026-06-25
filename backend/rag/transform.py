"""Query transformation — routed, not stacked. Each fixes a distinct failure mode.

- MultiQuery: vocabulary mismatch (paraphrase + union). Cheap, safe default.
- HyDE: terse/conceptual queries — embed a hypothetical answer, but keep the
  reranker scoring against the REAL question so a bad hypothetical can't smuggle
  in junk.
- Decomposition: multi-hop questions — split into sub-questions, retrieve each,
  merge.

Each wraps the reranking retriever (a ContextualCompressionRetriever), so the
output is already reranked. All rewriting runs on cheap Haiku.
"""

from __future__ import annotations

import json

from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from core.settings import get_settings

_rewrite_llm = ChatAnthropic(model=get_settings().model_router, max_tokens=1024)


def multiquery_retriever(base):
    return MultiQueryRetriever.from_llm(retriever=base, llm=_rewrite_llm)


_hyde_prompt = ChatPromptTemplate.from_template(
    "Write a short, factual passage that would answer this engineering "
    "question, as if from internal documentation. Question: {question}"
)
_hyde_chain = _hyde_prompt | _rewrite_llm


def hyde_retriever(base: ContextualCompressionRetriever) -> RunnableLambda:
    def _retrieve(question: str) -> list[Document]:
        hypothetical = _hyde_chain.invoke({"question": question}).content
        # Retrieval uses the hypothetical; rerank still scores the REAL question.
        docs = base.base_retriever.invoke(hypothetical)
        compressed = base.base_compressor.compress_documents(docs, query=question)
        return list(compressed)

    return RunnableLambda(_retrieve)


_decompose_prompt = ChatPromptTemplate.from_template(
    "Break this question into 2-4 standalone sub-questions that can each be "
    "researched independently. Return a JSON array of strings only.\n\n{question}"
)
_decompose_chain = _decompose_prompt | _rewrite_llm


def decomposition_retriever(base) -> RunnableLambda:
    def _retrieve(question: str) -> list[Document]:
        sub_qs = json.loads(_decompose_chain.invoke({"question": question}).content)
        seen: set[str] = set()
        merged: list[Document] = []
        for sub_q in sub_qs:
            for doc in base.invoke(sub_q):
                key = doc.metadata.get("id") or doc.page_content[:64]
                if key not in seen:
                    seen.add(key)
                    merged.append(doc)
        return merged

    return RunnableLambda(_retrieve)
