"""Tiered ChatAnthropic registry for the LCEL chains and the LangGraph agent.

These are the LangChain-wrapped models (Runnables) — distinct from the raw-SDK
client in client.py that answer() uses for citation/stream control. Building
generation both ways is deliberate: the raw SDK where Anthropic-specific knobs
matter, LangChain where composability/observability do.

Claude 4.x gotchas: adaptive thinking only (NO budget_tokens), and NO
temperature/top_p/top_k — steer depth with output_config.effort.
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic

from core.settings import get_settings

_s = get_settings()
_key = _s.anthropic_api_key.get_secret_value()

# Workhorse: most RAG answers run here.
llm_sonnet = ChatAnthropic(model=_s.model_workhorse, max_tokens=4096, api_key=_key)

# Hard queries / final synthesis when the router escalates.
llm_opus = ChatAnthropic(
    model=_s.model_hard,
    max_tokens=8192,
    thinking={"type": "adaptive"},  # NO budget_tokens (removed on 4.x)
    model_kwargs={"output_config": {"effort": "high"}},
    api_key=_key,
)

# Cheap, fast classification: routing + document/hallucination grading.
llm_haiku = ChatAnthropic(model=_s.model_router, max_tokens=1024, api_key=_key)
