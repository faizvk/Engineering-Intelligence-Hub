"""Structured logging emits valid JSON with the request_id field. Pure-stdlib."""

import json
import logging

from core.logging import JsonFormatter


def test_json_formatter_emits_valid_json():
    rec = logging.LogRecord("eih", logging.INFO, __file__, 1, "hello", None, None)
    out = json.loads(JsonFormatter().format(rec))
    assert out["level"] == "INFO"
    assert out["msg"] == "hello"
    assert out["logger"] == "eih"


def test_request_id_included_when_present():
    rec = logging.LogRecord("eih", logging.INFO, __file__, 1, "x", None, None)
    rec.request_id = "abc123"
    assert json.loads(JsonFormatter().format(rec))["request_id"] == "abc123"
