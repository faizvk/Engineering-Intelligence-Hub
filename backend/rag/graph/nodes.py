"""Graph nodes: each is a plain function RAGState -> partial RAGState.

Graders run ONCE here and write their verdict to state; the conditional edges
branch on the stored value (they do not re-run the grader, which would double the
Haiku calls).
"""

from __future__ import annotations

from backend.llm.models import llm_haiku, llm_opus, llm_sonnet
from backend.rag.chain import format_docs, prompt
from backend.rag.graph.graders import doc_grader, halluc_grader, query_router
from backend.rag.graph.state import RAGState
from backend.rag.pipeline import retrieve as pipeline_retrieve


def route(state: RAGState) -> RAGState:
    res = query_router.invoke(
        f"Is this answerable from an engineering knowledge base? {state['question']}"
    )
    return {"route": "vectorstore" if res.datasource == "vectorstore" else "reject"}


def retrieve(state: RAGState) -> RAGState:
    # route=False: the graph already routed; keep retrieval deterministic here.
    docs = pipeline_retrieve(state["question"], route=False)
    return {"documents": docs}


def grade_documents(state: RAGState) -> RAGState:
    res = doc_grader.invoke(
        f"Question: {state['question']}\n\nDocs:\n{format_docs(state['documents'])}"
    )
    return {"docs_relevant": bool(res.relevant)}


def rewrite_query(state: RAGState) -> RAGState:
    rewritten = llm_haiku.invoke(
        f"Rewrite this query to retrieve better KB results: {state['question']}"
    ).content
    return {"question": rewritten, "retries": 1}  # +1 via the `add` reducer


def generate(state: RAGState) -> RAGState:
    # Escalate to Opus once we've already retried — a hard-query signal.
    llm = llm_opus if state.get("retries", 0) >= 1 else llm_sonnet
    chain = prompt | llm
    msg = chain.invoke({"context": format_docs(state["documents"]), "question": state["question"]})
    return {"generation": msg.content, "gen_attempts": 1}


def check_hallucination(state: RAGState) -> RAGState:
    res = halluc_grader.invoke(
        f"Context:\n{format_docs(state['documents'])}\n\nAnswer: {state['generation']}"
    )
    return {"grounded": bool(res.grounded)}


def reject(state: RAGState) -> RAGState:
    return {"generation": "This question is out of scope for the engineering knowledge base."}
