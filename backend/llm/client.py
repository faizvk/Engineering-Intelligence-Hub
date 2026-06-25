"""Shared Anthropic client + model constants.

One client per process; the SDK handles connection pooling and retries
(429/408/409/5xx with exponential backoff). Model IDs come from settings so
they're configurable, but the defaults are the verified, stable IDs — never
append date suffixes.
"""

from __future__ import annotations

import anthropic

from core.settings import get_settings

_s = get_settings()

# Tunable retries + per-request timeout; the SDK backs off automatically.
client = anthropic.Anthropic(
    api_key=_s.anthropic_api_key.get_secret_value(),
    max_retries=3,
    timeout=60.0,
)

ROUTER_MODEL = _s.model_router      # claude-haiku-4-5  ($1 / $5)
DEFAULT_MODEL = _s.model_workhorse  # claude-sonnet-4-6 ($3 / $15)  workhorse
HARD_MODEL = _s.model_hard          # claude-opus-4-8   ($5 / $25)  hard reasoning
