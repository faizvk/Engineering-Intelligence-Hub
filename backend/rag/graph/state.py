"""The single typed state object every node reads and writes.

retries accumulates across rewrite loops; gen_attempts across regenerate loops.
Both are bounded in edges.py so neither loop can run away.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, TypedDict

from langchain_core.documents import Document


class RAGState(TypedDict, total=False):
    question: str
    documents: list[Document]
    generation: str
    route: str  # "vectorstore" | "reject"
    docs_relevant: bool  # written by grade_documents, read by the edge
    grounded: bool  # written by check_hallucination, read by the edge
    retries: Annotated[int, add]  # rewrite-loop counter
    gen_attempts: Annotated[int, add]  # regenerate-loop counter
