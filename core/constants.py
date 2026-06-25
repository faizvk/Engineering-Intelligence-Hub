"""Verified, load-bearing platform facts — kept dependency-free so anything
(cost meter, router, tests) can import them without pulling in heavy deps.

Pricing is USD per 1M tokens (input / output). Claude model IDs are stable and
verified — never append date suffixes. Voyage's lineup changes; verify names
and dimensions on docs.voyageai.com before relying on specifics.
"""

from __future__ import annotations

# USD per 1M tokens.
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-8": {"in": 5.00, "out": 25.00},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5": {"in": 1.00, "out": 5.00},
}

# Cache reads bill at ~0.1x input; 5-min cache writes at 1.25x, 1-hour at 2x.
CACHE_READ_MULT = 0.10
CACHE_WRITE_MULT = 1.25  # 5-minute TTL

# Minimum cacheable prefix length (a shorter system prompt silently won't cache).
MIN_CACHE_PREFIX_TOKENS: dict[str, int] = {
    "claude-opus-4-8": 4096,
    "claude-haiku-4-5": 4096,
    "claude-sonnet-4-6": 2048,
}

# Context window / max output tokens, per model.
CONTEXT_WINDOW: dict[str, int] = {
    "claude-opus-4-8": 1_000_000,
    "claude-sonnet-4-6": 1_000_000,
    "claude-haiku-4-5": 200_000,
}
MAX_OUTPUT_TOKENS: dict[str, int] = {
    "claude-opus-4-8": 128_000,
    "claude-sonnet-4-6": 64_000,
    "claude-haiku-4-5": 64_000,
}
