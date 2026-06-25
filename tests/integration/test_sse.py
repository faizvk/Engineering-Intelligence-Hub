"""SSE wiring: frame format, and the no-answer short-circuit on the stream path."""

import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("anthropic")
pytest.importorskip("langchain_core")


def test_sse_frame_round_trips():
    from backend.api.query import _sse

    frame = _sse("token", {"text": "hi"})
    assert frame.startswith("event: token\n")
    assert frame.endswith("\n\n")
    ev = frame.split("\n", 1)[0].removeprefix("event: ")
    data = json.loads(frame.split("data: ", 1)[1])
    assert ev == "token" and data["text"] == "hi"


@pytest.mark.asyncio
async def test_stream_no_answer_short_circuits(monkeypatch):
    pytest.importorskip("pytest_asyncio")
    import backend.rag.service as svc
    from backend.rag.scoring import NO_ANSWER

    # No retrieved chunks -> honest no-answer, no Claude call.
    monkeypatch.setattr(svc, "retrieve", lambda *a, **k: [])
    events = [ev async for ev in svc.stream_query("anything")]
    assert events == [("token", {"text": NO_ANSWER})]
