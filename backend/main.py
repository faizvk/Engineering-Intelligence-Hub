"""FastAPI app factory + router wiring.

Routers are thin: validate input, hand off to the RAG orchestration layer, and
stream or return. Business logic stays out of the route handlers. Additional
routers (query, ingest, feedback) are wired in as later phases land them.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import feedback, health, query
from core.db import dispose_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # startup: the pool is lazy-initialized on first use
    await dispose_engine()  # shutdown: cleanly close the connection pool


def create_app() -> FastAPI:
    from core.tracing import configure_langsmith

    configure_langsmith()  # no-op unless LANGSMITH_TRACING is set
    app = FastAPI(
        title="Engineering Intelligence Hub",
        version="0.1.0",
        lifespan=lifespan,
    )
    # CORS: allow exactly the frontend origin(s), configurable per environment.
    origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins if o.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(query.router)
    app.include_router(feedback.router)
    return app


app = create_app()
