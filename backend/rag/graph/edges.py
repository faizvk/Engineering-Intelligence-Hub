"""Conditional-edge functions: return the NAME of the next node.

They read the grade already stored in state (graded once in the node) and bound
both loops — the rewrite loop on `retries`, the regenerate loop on `gen_attempts`
— so neither can spin forever.
"""

from __future__ import annotations

from backend.rag.graph.state import RAGState

MAX_RETRIES = 2
MAX_GEN_ATTEMPTS = 2


def decide_route(state: RAGState) -> str:
    return "retrieve" if state.get("route") == "vectorstore" else "reject"


def decide_after_grading(state: RAGState) -> str:
    if state.get("docs_relevant"):
        return "generate"
    # Weak docs: rewrite and retry, but give up gracefully at the cap.
    return "rewrite_query" if state.get("retries", 0) < MAX_RETRIES else "generate"


def decide_after_generation(state: RAGState) -> str:
    if state.get("grounded") or state.get("gen_attempts", 0) >= MAX_GEN_ATTEMPTS:
        return "end"
    return "generate"  # ungrounded -> regenerate (bounded by MAX_GEN_ATTEMPTS)
