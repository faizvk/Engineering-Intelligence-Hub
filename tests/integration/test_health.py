"""The app builds and exposes /health. Skipped automatically where the web
stack isn't installed, so the suite stays green in a bare environment.
"""

import pytest


def test_health_route_registered():
    pytest.importorskip("fastapi")
    pytest.importorskip("sqlalchemy")
    from backend.main import create_app

    app = create_app()
    paths = {getattr(r, "path", None) for r in app.routes}
    assert "/health" in paths
