"""Database access: async SQLAlchemy engine for the API, a raw psycopg path for
the vector/FTS retrievers, and a couple of small pgvector helpers.

We standardize the async engine on the psycopg3 driver (``postgresql+psycopg://``)
because psycopg3 is both sync- and async-capable, so a single DATABASE_URL serves
the FastAPI request path and the ingestion CLI.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

import psycopg
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.settings import get_settings

_settings = get_settings()

# Connection pooling, sized for the worker count (see deployment notes).
engine = create_async_engine(
    _settings.database_url,
    pool_size=10,  # steady connections per process
    max_overflow=10,  # burst headroom
    pool_pre_ping=True,  # drop dead connections (managed PG recycles them)
    pool_recycle=1800,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session and closes it after the request."""
    async with SessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    """Shutdown hook: cleanly close the connection pool."""
    await engine.dispose()


def raw_connect() -> psycopg.Connection:
    """A plain psycopg3 connection for the dense/lexical retrievers.

    Uses the non-SQLAlchemy DSN (no +driver suffix). pgvector adapters are
    registered so Python lists bind to the ``vector`` type automatically.
    """
    conn = psycopg.connect(_settings.database_url_raw)
    try:
        from pgvector.psycopg import register_vector

        register_vector(conn)
    except Exception:
        # If pgvector adapters aren't available, callers can fall back to
        # vector_literal() + an explicit ::vector cast.
        pass
    return conn


def vector_literal(embedding: Sequence[float]) -> str:
    """Render an embedding as a pgvector text literal: ``[0.1,0.2,...]``.

    Bind with an explicit cast — ``%s::vector`` — when pgvector's psycopg
    adapter is not registered on the connection.
    """
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"
