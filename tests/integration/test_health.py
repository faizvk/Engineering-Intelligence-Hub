"""/health responds (200 when the DB is reachable, 503 when not) and unknown
routes 404. Behavioral via TestClient — robust across FastAPI versions (newer
ones lazily wrap included routers, so inspecting app.routes[*].path is brittle).
Skipped where the web stack isn't installed.
"""

import pytest


def test_health_route_responds():
    pytest.importorskip("fastapi")
    pytest.importorskip("sqlalchemy")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from backend.main import create_app

    client = TestClient(create_app(), raise_server_exceptions=False)
    # Route exists: 200 if Postgres is up, 503 if it's unreachable — not 404.
    assert client.get("/health").status_code in (200, 503)
    assert client.get("/no-such-route").status_code == 404
