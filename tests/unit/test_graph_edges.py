"""The conditional edges branch on the stored grade and bound both loops, so the
agent can't spin forever. Skipped where langchain isn't installed.
"""

import pytest

pytest.importorskip("langchain_core")

from backend.rag.graph.edges import (  # noqa: E402
    MAX_GEN_ATTEMPTS,
    MAX_RETRIES,
    decide_after_generation,
    decide_after_grading,
    decide_route,
)


def test_route_branches():
    assert decide_route({"route": "vectorstore"}) == "retrieve"
    assert decide_route({"route": "reject"}) == "reject"


def test_relevant_docs_go_to_generate():
    assert decide_after_grading({"docs_relevant": True, "retries": 0}) == "generate"


def test_weak_docs_rewrite_until_cap():
    assert decide_after_grading({"docs_relevant": False, "retries": 0}) == "rewrite_query"
    # At the cap, give up gracefully and generate rather than loop forever.
    assert decide_after_grading({"docs_relevant": False, "retries": MAX_RETRIES}) == "generate"


def test_grounded_ends_else_regenerates_until_cap():
    assert decide_after_generation({"grounded": True, "gen_attempts": 1}) == "end"
    assert decide_after_generation({"grounded": False, "gen_attempts": 1}) == "generate"
    assert decide_after_generation({"grounded": False, "gen_attempts": MAX_GEN_ATTEMPTS}) == "end"
