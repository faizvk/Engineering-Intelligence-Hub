"""Model tiering: route before you generate.

A cheap Haiku classification decides difficulty and picks the tier — most
queries go to Sonnet, only genuinely hard cross-system/multi-hop reasoning
escalates to Opus. This is the single best cost lever in the project.

The router is the ONE place we use structured outputs: a classification has no
citations, so output_config.format is free to use and json.loads is trivial.
(Citations are incompatible with structured outputs, so the answer call cannot
use both.)
"""

from __future__ import annotations

import json

from backend.llm.client import DEFAULT_MODEL, HARD_MODEL, ROUTER_MODEL, client

_ROUTER_SYSTEM = (
    "You are a query router for an engineering documentation assistant. "
    "Classify the user's question by the reasoning it requires:\n"
    "- 'simple': a direct lookup answerable from one document or a definition.\n"
    "- 'hard': requires synthesizing across multiple documents, reasoning over "
    "an incident timeline, or tracing cause/effect across systems.\n"
    "Return only the classification."
)

_ROUTER_SCHEMA = {
    "type": "object",
    "properties": {
        "difficulty": {"type": "string", "enum": ["simple", "hard"]},
        "reason": {"type": "string"},
    },
    "required": ["difficulty", "reason"],
    "additionalProperties": False,
}


def route(question: str) -> str:
    """Return the model ID to use for this question. Cheap Haiku classification."""
    resp = client.messages.create(
        model=ROUTER_MODEL,
        max_tokens=256,
        system=_ROUTER_SYSTEM,
        messages=[{"role": "user", "content": question}],
        output_config={"format": {"type": "json_schema", "schema": _ROUTER_SCHEMA}},
    )
    text = next(b.text for b in resp.content if b.type == "text")
    difficulty = json.loads(text)["difficulty"]
    return HARD_MODEL if difficulty == "hard" else DEFAULT_MODEL
