"""The Haiku router maps its JSON verdict to the right model tier (no real call)."""

from types import SimpleNamespace

import pytest

pytest.importorskip("anthropic")


def _fake_response(json_text: str):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=json_text)])


def test_hard_routes_to_opus(monkeypatch):
    from backend.llm import router

    monkeypatch.setattr(
        router.client.messages,
        "create",
        lambda **kw: _fake_response('{"difficulty":"hard","reason":"multi-system"}'),
    )
    assert router.route("trace this across systems") == router.HARD_MODEL


def test_simple_routes_to_sonnet(monkeypatch):
    from backend.llm import router

    monkeypatch.setattr(
        router.client.messages,
        "create",
        lambda **kw: _fake_response('{"difficulty":"simple","reason":"lookup"}'),
    )
    assert router.route("what is the access token TTL?") == router.DEFAULT_MODEL
