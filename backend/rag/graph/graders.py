"""Structured-output graders: routing, relevance, and grounding all need a typed
yes/no, so they use Claude structured outputs via with_structured_output().

These are separate nodes from generate (which uses citations) because citations
are incompatible with structured outputs.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.llm.models import llm_haiku


class GradeDocuments(BaseModel):
    """Binary relevance check for retrieved documents."""

    relevant: bool = Field(description="Do the documents answer the question?")


class GradeHallucination(BaseModel):
    """Is the generated answer grounded in the retrieved documents?"""

    grounded: bool = Field(description="Is every claim supported by the context?")


class RouteQuery(BaseModel):
    """Route a query to retrieval or rejection."""

    datasource: str = Field(description="'vectorstore' or 'reject'")


doc_grader = llm_haiku.with_structured_output(GradeDocuments)
halluc_grader = llm_haiku.with_structured_output(GradeHallucination)
query_router = llm_haiku.with_structured_output(RouteQuery)
