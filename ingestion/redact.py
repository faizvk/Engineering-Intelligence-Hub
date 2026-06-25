"""PII & secret redaction, applied by every loader before chunking.

Incident reports and Slack threads leak credentials, tokens, customer emails,
and internal hostnames. Once a secret is embedded into Postgres it is
effectively persisted and can resurface in an answer — so scrub at ingestion.
For higher recall, add a presidio/NER pass for names and locations.
"""

from __future__ import annotations

import re

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    (re.compile(r"\b(sk-ant-|pa-|ghp_|xox[baprs]-)[A-Za-z0-9_-]{8,}\b"), "[SECRET]"),
    (re.compile(r"\baws_secret_access_key\s*=\s*\S+", re.I), "aws_secret_access_key=[REDACTED]"),
    (
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.S,
        ),
        "[PRIVATE_KEY]",
    ),
]


def redact(text: str) -> str:
    for pat, repl in _PATTERNS:
        text = pat.sub(repl, text)
    return text
