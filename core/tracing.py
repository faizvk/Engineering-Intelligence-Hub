"""LangSmith tracing setup — a deployment concern shared by the API and the eval
harness, so it lives in the shared kernel (not in evals/, which backend must not
import). Translates typed settings into the env vars LangChain reads; with
LCEL/LangGraph, that's all tracing needs.
"""

from __future__ import annotations

import os

from core.settings import get_settings


def configure_langsmith() -> bool:
    """Enable tracing if configured. Returns True if it was turned on."""
    s = get_settings()
    if not (s.langsmith_tracing and s.langsmith_api_key):
        return False
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ["LANGSMITH_API_KEY"] = s.langsmith_api_key.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = s.langsmith_project
    return True
