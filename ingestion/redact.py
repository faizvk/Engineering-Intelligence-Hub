"""PII & secret redaction, applied by every loader before chunking.

Once a secret is embedded into Postgres it is effectively persisted and can
resurface in an answer — so scrub at ingestion. Regex covers the common,
high-confidence secrets; register_redactor() is the hook for a presidio/NER pass
(names, locations, account numbers) that needs ML, kept optional so the base
pipeline has no heavy dependency.
"""

from __future__ import annotations

import re
from typing import Callable

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    # Provider key prefixes: Anthropic, Voyage, GitHub, Slack.
    (re.compile(r"\b(sk-ant-|pa-|ghp_|xox[baprs]-)[A-Za-z0-9_-]{8,}\b"), "[SECRET]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS_KEY_ID]"),
    (re.compile(r"\baws_secret_access_key\s*=\s*\S+", re.I), "aws_secret_access_key=[REDACTED]"),
    # JWTs: header.payload.signature, base64url.
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "[JWT]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{10,}"), "Bearer [REDACTED]"),
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.S,
        ),
        "[PRIVATE_KEY]",
    ),
]

# Optional extra passes (e.g. a presidio/NER redactor) registered at startup.
_EXTRA_REDACTORS: list[Callable[[str], str]] = []


def register_redactor(fn: Callable[[str], str]) -> None:
    """Plug in an additional redaction pass (applied after the regex patterns)."""
    _EXTRA_REDACTORS.append(fn)


def redact(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    for fn in _EXTRA_REDACTORS:
        text = fn(text)
    return text
