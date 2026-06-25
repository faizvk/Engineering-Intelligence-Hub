"""Query-intent routing: classify a query into a metadata filter and a retrieval
strategy with a cheap Haiku call.

A troubleshooting query biases toward recent incident reports; an onboarding
query toward docs and code. pgvector applies the filter inside the ANN search
(pre-filter), so the k candidates stay relevant. The same Haiku classification
doubles as a cost lever (it also informs the generation tier).

Time filters are computed as ISO timestamps in Python — NOT as SQL strings like
"now() - interval '90 days'", which a metadata filter would treat as a literal.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from core.settings import get_settings

_s = get_settings()
_router_llm = ChatAnthropic(model=_s.model_router, max_tokens=512)

_route_prompt = ChatPromptTemplate.from_template(
    """Classify this engineering query and return JSON only:
{{"intent": "incident" | "docs" | "code" | "general",
  "repo": <repo name if one is clearly referenced, else null>}}

Query: {query}"""
)
_route_chain = _route_prompt | _router_llm

_strategy_llm = ChatAnthropic(model=_s.model_router, max_tokens=256)
_strategy_prompt = ChatPromptTemplate.from_template(
    """Pick the best retrieval strategy for this query. Return JSON only:
{{"strategy": "none" | "multiquery" | "hyde" | "decomposition"}}

- "none": exact identifiers, error codes, function/API names
- "multiquery": short conversational questions
- "hyde": terse conceptual "how does X work" questions
- "decomposition": compound, multi-hop questions

Query: {query}"""
)
_strategy_chain = _strategy_prompt | _strategy_llm


def build_filter(query: str) -> dict:
    """Turn an intent classification into a metadata filter dict."""
    route = json.loads(_route_chain.invoke({"query": query}).content)
    f: dict = {}
    intent = route.get("intent")
    if intent == "incident":
        f["doc_type"] = {"$eq": "incident"}
        cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        f["created_at"] = {"$gte": cutoff}  # ISO literal, computed in Python
    elif intent == "docs":
        f["doc_type"] = {"$in": ["doc", "diagram"]}
    elif intent == "code":
        f["doc_type"] = {"$eq": "code"}
    if route.get("repo"):
        f["repo"] = {"$eq": route["repo"]}
    return f


def choose_strategy(query: str) -> str:
    return json.loads(_strategy_chain.invoke({"query": query}).content)["strategy"]
